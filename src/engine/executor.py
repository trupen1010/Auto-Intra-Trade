"""Orchestration of the complete backtest pipeline.

This module sequences all upstream components to execute a full candle-by-candle
backtest simulation without lookahead bias.
"""

from __future__ import annotations

import logging
import sqlite3
from datetime import date
from zoneinfo import ZoneInfo

from src.data.validator import validate_candle_sequence
from src.db.repository import CandleRepository
from src.engine.exceptions import ExecutionError
from src.engine.simulator import run_simulation
from src.indicators.atr import compute_atr
from src.indicators.mtf_state import resolve_mtf_alignment
from src.indicators.signals import detect_signals
from src.indicators.trailing_stop import compute_trailing_stop
from src.models.backtest_config import BacktestConfig
from src.models.signal_state import SignalTransition
from src.models.simulation_result import SimulationResult
from src.utils.datetime_utils import candle_close_time
from src.utils.enums import SignalSide, Timeframe

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


def execute_backtest(
    symbol: str,
    start_date: date,
    end_date: date,
    config: BacktestConfig,
    conn: sqlite3.Connection,
) -> SimulationResult:
    """Execute a complete candle-by-candle backtest simulation.

    Orchestrates the full pipeline:
      1. Load 1D, 15m, 5m candles from storage
      2. Validate each series
      3. Compute ATR and trailing stop for each timeframe
      4. Generate signal transitions
      5. Resolve multi-timeframe alignments (no lookahead)
      6. Run candle-by-candle simulation

    Args:
        symbol: Instrument symbol to backtest.
        start_date: Inclusive start date for candle range.
        end_date: Inclusive end date for candle range.
        config: Configuration with capital, risk, ATR params, charges config.
        conn: Open SQLite connection for candle retrieval.

    Returns:
        SimulationResult with completed trades and rejected trades.

    Raises:
        ExecutionError: If any validation or processing stage fails.
    """

    try:
        logger.info(f"Starting backtest for {symbol} from {start_date} to {end_date}")

        start_dt = _to_ist_datetime(start_date)
        end_dt = _to_ist_datetime(end_date)

        # 1. Load candles from all three timeframes.
        logger.info("Loading 1D candles...")
        candles_1d = CandleRepository.fetch_candles(
            conn, symbol, Timeframe.ONE_DAY, start_dt, end_dt
        )

        logger.info("Loading 15m candles...")
        candles_15m = CandleRepository.fetch_candles(
            conn, symbol, Timeframe.FIFTEEN_MINUTE, start_dt, end_dt
        )

        logger.info("Loading 5m candles...")
        candles_5m = CandleRepository.fetch_candles(
            conn, symbol, Timeframe.FIVE_MINUTE, start_dt, end_dt
        )

        # 2. Validate each series.
        logger.info("Validating candle sequences...")
        validate_candle_sequence(candles_1d, Timeframe.ONE_DAY, symbol)
        validate_candle_sequence(candles_15m, Timeframe.FIFTEEN_MINUTE, symbol)
        validate_candle_sequence(candles_5m, Timeframe.FIVE_MINUTE, symbol)

        # 3. Compute ATR for all timeframes.
        logger.info("Computing ATR values...")
        atr_1d = compute_atr(candles_1d, config.atr_period)
        atr_15m = compute_atr(candles_15m, config.atr_period)
        atr_5m = compute_atr(candles_5m, config.atr_period)

        # 4. Compute trailing stops and signals.
        logger.info("Computing trailing stops and signals...")
        trail_5m, sides_5m = compute_trailing_stop(
            candles_5m, atr_5m, config.atr_sensitivity
        )
        signals_5m = detect_signals(sides_5m)

        trail_15m, sides_15m = compute_trailing_stop(
            candles_15m, atr_15m, config.atr_sensitivity
        )
        signals_15m_raw = detect_signals(sides_15m)

        trail_1d, sides_1d = compute_trailing_stop(
            candles_1d, atr_1d, config.atr_sensitivity
        )
        signals_1d = detect_signals(sides_1d)

        # 5. Resolve multi-timeframe alignments (no lookahead).
        logger.info("Resolving multi-timeframe alignments...")
        mtf_alignments = [
            resolve_mtf_alignment(
                ts_5m=candle.timestamp,
                signals_1d=signals_1d,
                signals_15m=signals_15m_raw,
                candles_1d=candles_1d,
                candles_15m=candles_15m,
            )
            for candle in candles_5m
        ]

        # Map 15m signals to 5m grid for input to simulator.
        signals_15m_5m_grid = _map_signals_to_5m_grid(
            signals_15m_raw, candles_15m, candles_5m
        )

        # Populate computed state in config for simulator.
        config.atr_values_5m = atr_5m
        config.trailing_stop_5m = trail_5m

        # 6. Run the simulation.
        logger.info("Running candle-by-candle simulation...")
        result = run_simulation(
            candles_5m=candles_5m,
            signals_5m=signals_5m,
            signals_15m=signals_15m_5m_grid,
            mtf_alignments=mtf_alignments,
            config=config,
        )

        logger.info(
            f"Backtest complete: {len(result.trades)} trades, "
            f"{len(result.rejected_trades)} rejected"
        )
        return result

    except ExecutionError:
        raise
    except Exception as e:
        msg = f"Backtest execution failed: {e}"
        logger.exception(msg)
        raise ExecutionError(msg) from e


def _to_ist_datetime(d: date) -> object:
    """Convert a date to an IST-aware datetime at midnight."""
    from datetime import datetime

    return datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=IST)


def _map_signals_to_5m_grid(
    signals_15m: list,
    candles_15m: list,
    candles_5m: list,
) -> list:
    """Map 15m signals to 5m grid using latest-available logic.

    For each 5m candle, finds the latest 15m signal available without lookahead.
    A 15m signal is available at a 5m timestamp if the 15m candle close time
    is less than or equal to the 5m timestamp.

    Args:
        signals_15m: Signal transitions from 15m candles.
        candles_15m: 15m candles (source of signals).
        candles_5m: 5m candles (target grid).

    Returns:
        List of signals with same length as candles_5m, where each entry is
        the latest available 15m signal at that 5m timestamp.
    """

    mapped = []
    latest_15m_signal = SignalSide.NEUTRAL
    latest_15m_index = 0

    for candle_5m in candles_5m:
        # Find the latest 15m signal available as of this 5m timestamp.
        ts_5m = candle_5m.timestamp
        for idx in range(latest_15m_index, len(candles_15m)):
            candle_15m = candles_15m[idx]
            close_time = candle_close_time(
                candle_15m.timestamp, candle_15m.timeframe
            )
            if close_time <= ts_5m:
                latest_15m_signal = signals_15m[idx].side
                latest_15m_index = idx
            else:
                break

        # Create a signal transition for this 5m bar, marking it non-fresh
        # (only fresh when we've advanced to a new 15m bar).
        is_fresh = False
        if latest_15m_index > 0:
            prev_side = signals_15m[latest_15m_index - 1].side
            is_fresh = prev_side != latest_15m_signal
        mapped.append(
            SignalTransition(
                side=latest_15m_signal, is_fresh=is_fresh, bar_index=len(mapped)
            )
        )

    return mapped
