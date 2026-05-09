"""Integration tests for the backtest executor."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.db.repository import CandleRepository
from src.db.schema import create_all_tables
from src.engine.exceptions import ExecutionError
from src.engine.executor import execute_backtest
from src.models.candle import Candle
from src.utils.exceptions import InsufficientDataError

IST = ZoneInfo("Asia/Kolkata")


@dataclass
class _Cfg:
    """Test executor configuration."""

    run_id: str = "test_run"
    symbol: str = "TESTSTOCK"
    initial_capital: float = 100_000.0
    risk_per_trade_pct: float = 0.01
    sl_atr_multiplier: float = 2.0
    entry_cutoff_time: time = time(15, 10)
    session_end_time: time = time(15, 30)
    atr_period: int = 3
    atr_sensitivity: int = 2
    atr_values_5m: list[float] = field(default_factory=list)
    trailing_stop_5m: list[float | None] = field(default_factory=list)

    @dataclass(slots=True)
    class _Charges:
        brokerage_cap_per_order: float = 20.0
        brokerage_pct: float = 0.0003
        stt_sell_pct: float = 0.00025
        transaction_pct: float = 0.0000345
        gst_pct: float = 0.18
        sebi_pct: float = 0.000001
        stamp_duty_buy_pct: float = 0.00003

    charges: _Charges = field(default_factory=_Charges)


def _dt(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    """Create an IST-aware datetime."""
    return datetime(year, month, day, hour, minute, tzinfo=IST)


def _candle(
    ts: datetime, o: float, h: float, l: float, c: float, timeframe: str = "5m"
) -> Candle:
    """Create a test candle."""
    return Candle(
        symbol="TESTSTOCK",
        timeframe=timeframe,
        timestamp=ts,
        open=o,
        high=h,
        low=l,
        close=c,
        volume=1000.0,
    )


def _in_memory_db() -> sqlite3.Connection:
    """Create an in-memory SQLite database with schema."""
    conn = sqlite3.connect(":memory:")
    create_all_tables(conn)
    return conn


def test_full_pipeline_produces_simulation_result() -> None:
    """Test that a complete pipeline execution produces a SimulationResult."""
    conn = _in_memory_db()

    # Create synthetic 3-day data (1D + 15m + 5m).
    # 1D: 3 daily candles
    candles_1d = [
        _candle(_dt(2024, 1, 1, 0, 0), 100, 110, 95, 105, "1d"),
        _candle(_dt(2024, 1, 2, 0, 0), 105, 115, 100, 110, "1d"),
        _candle(_dt(2024, 1, 3, 0, 0), 110, 120, 105, 115, "1d"),
    ]

    # 15m: every 15 minutes from 9:15 to 15:30 (market hours: 6h 15m = 25 candles)
    candles_15m = []
    for day_offset in range(3):
        ts = _dt(2024, 1, 1, 9, 15) + timedelta(days=day_offset)
        end_time = _dt(2024, 1, 1, 15, 30) + timedelta(days=day_offset)
        while ts <= end_time:
            candles_15m.append(
                _candle(ts, 100 + day_offset * 5, 110, 95, 105, "15m")
            )
            ts += timedelta(minutes=15)

    # 5m: every 5 minutes from 9:15 to 15:30 (market hours: 6h 15m = 75 candles)
    candles_5m = []
    for day_offset in range(3):
        ts = _dt(2024, 1, 1, 9, 15) + timedelta(days=day_offset)
        end_time = _dt(2024, 1, 1, 15, 30) + timedelta(days=day_offset)
        while ts <= end_time:
            candles_5m.append(_candle(ts, 100 + day_offset * 5, 110, 95, 105, "5m"))
            ts += timedelta(minutes=5)

    # Insert into database.
    CandleRepository.insert_candles(conn, candles_1d)
    CandleRepository.insert_candles(conn, candles_15m)
    CandleRepository.insert_candles(conn, candles_5m)

    # Execute backtest.
    cfg = _Cfg()
    result = execute_backtest(
        symbol="TESTSTOCK",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 3),
        config=cfg,
        conn=conn,
    )

    # Verify SimulationResult structure.
    assert result is not None
    assert result.run_id == "test_run"
    assert isinstance(result.trades, list)
    assert isinstance(result.rejected_trades, list)


def test_validation_failure_raises_execution_error() -> None:
    """Test that candle validation failure raises ExecutionError."""
    conn = _in_memory_db()

    # Create insufficient 1D candles (only 1, need at least 2 per validator).
    candles_1d = [_candle(_dt(2024, 1, 1, 0, 0), 100, 110, 95, 105, "1d")]

    # Create sufficient 15m and 5m candles.
    candles_15m = [
        _candle(_dt(2024, 1, 1, 9, 15), 100, 110, 95, 105, "15m"),
        _candle(_dt(2024, 1, 1, 10, 0), 105, 115, 100, 110, "15m"),
    ]
    candles_5m = [
        _candle(_dt(2024, 1, 1, 9, 15), 100, 110, 95, 105, "5m"),
        _candle(_dt(2024, 1, 1, 9, 20), 105, 115, 100, 110, "5m"),
    ]

    CandleRepository.insert_candles(conn, candles_1d)
    CandleRepository.insert_candles(conn, candles_15m)
    CandleRepository.insert_candles(conn, candles_5m)

    cfg = _Cfg()

    # ExecutionError should be raised due to insufficient 1D candles.
    with pytest.raises(ExecutionError):
        execute_backtest(
            symbol="TESTSTOCK",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 2),
            config=cfg,
            conn=conn,
        )


def test_empty_candles_raises_execution_error() -> None:
    """Test that empty candle lists raise ExecutionError."""
    conn = _in_memory_db()

    # Don't insert any candles. fetch_candles will return empty lists.
    cfg = _Cfg()

    # ExecutionError should be raised due to insufficient data.
    with pytest.raises(ExecutionError):
        execute_backtest(
            symbol="TESTSTOCK",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 3),
            config=cfg,
            conn=conn,
        )
