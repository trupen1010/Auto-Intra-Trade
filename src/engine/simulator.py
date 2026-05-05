"""Candle-by-candle simulation loop.

This module is responsible only for iterating over 5m candles and applying
entry/exit rules based on already-computed signals and multi-timeframe
alignment.
"""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

from src.engine.charges import calculate_round_trip_charges
from src.engine.position import OpenPosition
from src.engine.risk import compute_hard_sl, compute_position_size
from src.engine.trade_state import EngineTradeState
from src.models.candle import Candle
from src.models.mtf_alignment import MtfAlignment
from src.models.rejected_trade import RejectedTrade
from src.models.signal_state import SignalTransition
from src.models.simulation_result import SimulationResult
from src.utils.datetime_utils import validate_ist_datetime
from src.utils.enums import EntryTF, ExitReason, SignalSide


class BacktestConfig:  # pragma: no cover
    """Protocol-like stub for type checking.

    The real configuration model is defined in a later step. This stub keeps
    the simulator strongly typed without introducing a runtime dependency.
    """

    run_id: str
    symbol: str
    initial_capital: float
    risk_per_trade_pct: float
    sl_atr_multiplier: float
    session_end_time: time
    atr_values_5m: list[float]
    trailing_stop_5m: list[float | None]
    charges: object


def _session_end_dt(bar_time: datetime, session_end_time: object) -> datetime:
    """Build an IST-aware datetime for the configured session end."""

    if not isinstance(session_end_time, time):
        raise ValueError("session_end_time must be datetime.time")

    session_end_dt = datetime.combine(
        bar_time.date(), session_end_time, tzinfo=ZoneInfo("Asia/Kolkata")
    )
    validate_ist_datetime(session_end_dt, "session_end_time")
    return session_end_dt


def _compute_round_trip_charges(
    entry_price: float,
    exit_price: float,
    quantity: int,
    config: BacktestConfig,
) -> float:
    """Compute round-trip charges using the repository-standard formula."""

    charges = config.charges
    return calculate_round_trip_charges(
        entry_price=entry_price,
        exit_price=exit_price,
        quantity=quantity,
        brokerage_pct=float(charges.brokerage_pct),
        brokerage_cap_per_order=float(charges.brokerage_cap_per_order),
        stt_pct=float(charges.stt_sell_pct),
        exchange_pct=float(charges.transaction_pct),
        sebi_pct=float(charges.sebi_pct),
        gst_pct=float(charges.gst_pct),
        stamp_pct=float(charges.stamp_duty_buy_pct),
    )


def run_simulation(
    candles_5m: list[Candle],
    signals_5m: list[SignalTransition],
    mtf_alignments: list[MtfAlignment],
    config: BacktestConfig,
) -> SimulationResult:
    """Run a candle-by-candle simulation over 5m candles.

    Args:
        candles_5m: Ordered 5m candles (timestamp is candle open time).
        signals_5m: Per-bar signal transitions for 5m candles.
        mtf_alignments: Per-bar 1D/15m alignment snapshots resolved as-of each
            5m candle timestamp.
        config: Backtest configuration produced by the orchestration layer.
            Only the small subset of attributes referenced by
            :class:`~src.engine.simulator.BacktestConfig` are required.

    Returns:
        A :class:`~src.models.simulation_result.SimulationResult`.

    Raises:
        ValueError: If input list lengths do not match.
    """

    if not (len(candles_5m) == len(signals_5m) == len(mtf_alignments)):
        raise ValueError("candles_5m, signals_5m, and mtf_alignments must match length")

    trades: list[EngineTradeState] = []
    rejected_trades: list[RejectedTrade] = []
    open_position: OpenPosition | None = None
    last_exit_bar_index: int | None = None

    session_end_time = config.session_end_time

    for index, candle in enumerate(candles_5m):
        signal = signals_5m[index]
        alignment = mtf_alignments[index]

        if alignment.as_of != candle.timestamp:
            raise ValueError("mtf_alignments[i].as_of must match candles_5m[i].timestamp")

        exit_happened = False

        # A) EXIT CHECK (exit always has priority over entry).
        if open_position is not None:
            direction = open_position.trade.direction
            hard_sl = open_position.trade.hard_sl

            hard_sl_hit = (
                candle.low <= hard_sl if direction == SignalSide.BUY else candle.high >= hard_sl
            )
            if hard_sl_hit:
                exit_price = hard_sl
                exit_reason = ExitReason.HARD_SL
                exit_time = candle.timestamp
                charges = _compute_round_trip_charges(
                    entry_price=open_position.trade.entry_price,
                    exit_price=exit_price,
                    quantity=open_position.trade.quantity,
                    config=config,
                )
                trades.append(
                    open_position.to_closed_trade(
                        exit_time=exit_time,
                        exit_price=exit_price,
                        exit_reason=exit_reason,
                        charges=charges,
                    )
                )
                open_position = None
                exit_happened = True

            if not exit_happened:
                session_end_dt = _session_end_dt(candle.timestamp, session_end_time)
                if candle.timestamp >= session_end_dt:
                    exit_price = candle.close
                    exit_reason = ExitReason.TIME_EXIT
                    exit_time = candle.timestamp
                    charges = _compute_round_trip_charges(
                        entry_price=open_position.trade.entry_price,
                        exit_price=exit_price,
                        quantity=open_position.trade.quantity,
                        config=config,
                    )
                    trades.append(
                        open_position.to_closed_trade(
                            exit_time=exit_time,
                            exit_price=exit_price,
                            exit_reason=exit_reason,
                            charges=charges,
                        )
                    )
                    open_position = None
                    exit_happened = True

            if not exit_happened and signal.is_fresh:
                if (
                    open_position.trade.direction == SignalSide.BUY
                    and signal.side == SignalSide.SELL
                ) or (
                    open_position.trade.direction == SignalSide.SELL
                    and signal.side == SignalSide.BUY
                ):
                    if index + 1 < len(candles_5m):
                        exit_price = candles_5m[index + 1].open
                    else:
                        exit_price = candle.close
                    exit_reason = ExitReason.SIGNAL_EXIT
                    exit_time = candle.timestamp
                    charges = _compute_round_trip_charges(
                        entry_price=open_position.trade.entry_price,
                        exit_price=exit_price,
                        quantity=open_position.trade.quantity,
                        config=config,
                    )
                    trades.append(
                        open_position.to_closed_trade(
                            exit_time=exit_time,
                            exit_price=exit_price,
                            exit_reason=exit_reason,
                            charges=charges,
                        )
                    )
                    open_position = None
                    exit_happened = True

        if exit_happened:
            last_exit_bar_index = index

        # B) ENTRY CHECK.
        if open_position is None:
            if exit_happened:
                pass
            elif not signal.is_fresh:
                pass
            elif not alignment.aligned:
                pass
            elif index + 1 >= len(candles_5m):
                pass
            else:
                direction = signal.side
                if direction == SignalSide.NEUTRAL:
                    pass
                elif last_exit_bar_index is not None and last_exit_bar_index == index:
                    pass
                else:
                    entry_price = candles_5m[index + 1].open
                    atr_at_index = config.atr_values_5m[index]
                    hard_sl = compute_hard_sl(
                        entry_price=entry_price,
                        direction=direction,
                        atr=atr_at_index,
                        sl_atr_multiplier=config.sl_atr_multiplier,
                    )
                    quantity = compute_position_size(
                        capital=config.initial_capital,
                        risk_pct=config.risk_per_trade_pct,
                        entry_price=entry_price,
                        hard_sl_price=hard_sl,
                    )
                    if quantity == 0:
                        rejected_trades.append(
                            RejectedTrade(
                                symbol=config.symbol,
                                timestamp=candle.timestamp,
                                timeframe=candle.timeframe,
                                requested_side=(
                                    "LONG" if direction == SignalSide.BUY else "SHORT"
                                ),
                                reason="quantity=0",
                            )
                        )
                    else:
                        trade = EngineTradeState(
                            run_id=config.run_id,
                            symbol=config.symbol,
                            timeframe_entry=EntryTF.FIVE_MINUTE,
                            direction=direction,
                            entry_time=candles_5m[index + 1].timestamp,
                            entry_price=entry_price,
                            quantity=quantity,
                            hard_sl=hard_sl,
                        )
                        initial_stop = config.trailing_stop_5m[index]
                        if initial_stop is None:
                            raise ValueError("Trailing stop must not be None when entering")
                        open_position = OpenPosition(
                            trade=trade,
                            current_stop=float(initial_stop),
                            bars_held=0,
                        )

        # C) TRAILING STOP UPDATE.
        if open_position is not None:
            trailing_stop_at_index = config.trailing_stop_5m[index]
            if trailing_stop_at_index is not None:
                if open_position.trade.direction == SignalSide.BUY:
                    open_position.current_stop = max(
                        open_position.current_stop, trailing_stop_at_index
                    )
                elif open_position.trade.direction == SignalSide.SELL:
                    open_position.current_stop = min(
                        open_position.current_stop, trailing_stop_at_index
                    )
            open_position.bars_held += 1

    return SimulationResult(trades=trades, rejected_trades=rejected_trades, run_id=config.run_id)
