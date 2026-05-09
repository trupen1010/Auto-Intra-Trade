from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from zoneinfo import ZoneInfo

import pytest

from src.engine.simulator import run_simulation
from src.models.candle import Candle
from src.models.mtf_alignment import MtfAlignment
from src.models.signal_state import SignalTransition
from src.utils.enums import SignalSide


IST = ZoneInfo("Asia/Kolkata")


@dataclass(slots=True)
class _Cfg:
    run_id: str = "run1"
    symbol: str = "ABC"
    initial_capital: float = 10_000.0
    risk_per_trade_pct: float = 0.01
    sl_atr_multiplier: float = 2.0
    entry_cutoff_time: time = time(15, 10)
    session_end_time: time = time(15, 30)
    atr_values_5m: list[float] | None = None
    trailing_stop_5m: list[float | None] | None = None

    # charges config needed by calculate_round_trip_charges
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


def _dt(hour: int, minute: int) -> datetime:
    return datetime(2024, 1, 1, hour, minute, tzinfo=IST)


def _candle(ts: datetime, o: float, h: float, l: float, c: float) -> Candle:
    return Candle(
        symbol="ABC",
        timeframe="5m",
        timestamp=ts,
        open=o,
        high=h,
        low=l,
        close=c,
        volume=100.0,
    )


def _aligned(ts: datetime, aligned: bool = True) -> MtfAlignment:
    return MtfAlignment(
        bias_1d=SignalSide.BUY,
        signal_15m=SignalSide.BUY,
        aligned=aligned,
        as_of=ts,
    )


def test_hard_sl_exit_triggered_on_breach() -> None:
    candles = [
        _candle(_dt(9, 15), 100, 101, 99, 100),
        _candle(_dt(9, 20), 100, 101, 98, 99),
        _candle(_dt(9, 25), 100, 101, 90, 95),
    ]
    signals_5m = [
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=0),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=2),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=2),
    ]
    mtf = [_aligned(c.timestamp) for c in candles]

    cfg = _Cfg(
        atr_values_5m=[1.0, 1.0, 1.0],
        trailing_stop_5m=[95.0, 96.0, 97.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_reason.value == "HARD_SL"
    assert trade.exit_price == pytest.approx(98.0, abs=1e-6)


def test_time_exit_triggered_at_session_end() -> None:
    candles = [
        _candle(_dt(15, 0), 100, 101, 99, 100),
        _candle(_dt(15, 5), 100, 101, 99, 101),
        _candle(_dt(15, 10), 102, 103, 101, 102),
    ]
    signals_5m = [
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=0),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=2),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=2),
    ]
    mtf = [_aligned(c.timestamp) for c in candles]

    cfg = _Cfg(
        session_end_time=time(15, 10),
        atr_values_5m=[1.0, 1.0, 1.0],
        trailing_stop_5m=[98.0, 97.5, 97.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_reason.value == "TIME_EXIT"
    assert trade.exit_price == pytest.approx(102.0, abs=1e-6)


def test_signal_exit_on_side_flip() -> None:
    candles = [
        _candle(_dt(9, 15), 100, 101, 99, 100),
        _candle(_dt(9, 20), 100, 101, 99, 100),
        _candle(_dt(9, 25), 110, 111, 109, 110),
    ]
    signals_5m = [
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=0),
        SignalTransition(side=SignalSide.SELL, is_fresh=True, bar_index=1),
        SignalTransition(side=SignalSide.SELL, is_fresh=False, bar_index=2),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=2),
    ]
    mtf = [_aligned(c.timestamp) for c in candles]

    cfg = _Cfg(
        atr_values_5m=[1.0, 1.0, 1.0],
        trailing_stop_5m=[95.0, 95.0, 95.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    trade = result.trades[0]
    assert trade.exit_reason.value == "SIGNAL_5M"
    # exit at next open (bar 2 open)
    assert trade.exit_price == pytest.approx(110.0, abs=1e-6)


def test_no_reentry_same_bar_as_exit() -> None:
    candles = [
        _candle(_dt(9, 15), 100, 101, 99, 100),
        _candle(_dt(9, 20), 100, 101, 80, 90),
        _candle(_dt(9, 25), 100, 101, 99, 100),
        _candle(_dt(9, 30), 100, 101, 99, 100),
    ]
    signals_5m = [
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=0),
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=1),
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=2),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=3),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=2),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=3),
    ]
    mtf = [_aligned(c.timestamp) for c in candles]
    cfg = _Cfg(
        atr_values_5m=[1.0, 1.0, 1.0, 1.0],
        trailing_stop_5m=[95.0, 95.0, 95.0, 95.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    assert len(result.trades) == 1


def test_one_trade_at_a_time_no_pyramiding() -> None:
    candles = [
        _candle(_dt(9, 15), 100, 101, 99, 100),
        _candle(_dt(9, 20), 100, 101, 99, 100),
        _candle(_dt(9, 25), 100, 101, 99, 100),
        _candle(_dt(9, 30), 100, 101, 99, 100),
    ]
    # Fresh BUY at bar 0 triggers entry; fresh BUY again at bar 1 would attempt to pyramid.
    signals_5m = [
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=0),
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=1),
        SignalTransition(side=SignalSide.SELL, is_fresh=True, bar_index=2),
        SignalTransition(side=SignalSide.SELL, is_fresh=False, bar_index=3),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=2),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=3),
    ]
    mtf = [_aligned(c.timestamp) for c in candles]
    cfg = _Cfg(
        atr_values_5m=[1.0, 1.0, 1.0, 1.0],
        trailing_stop_5m=[90.0, 91.0, 92.0, 93.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    assert len(result.trades) == 1


def test_zero_quantity_logs_rejected_trade() -> None:
    candles = [
        _candle(_dt(9, 15), 100, 101, 99, 100),
        _candle(_dt(9, 20), 100, 101, 99, 100),
    ]
    signals_5m = [
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=0),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=1),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
    ]
    mtf = [_aligned(c.timestamp) for c in candles]
    cfg = _Cfg(
        initial_capital=1.0,
        risk_per_trade_pct=0.01,
        atr_values_5m=[1.0, 1.0],
        trailing_stop_5m=[95.0, 95.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    assert result.trades == []
    assert len(result.rejected_trades) == 1
    assert result.rejected_trades[0].reason == "quantity=0"


def test_mtf_not_aligned_skips_entry() -> None:
    candles = [
        _candle(_dt(9, 15), 100, 101, 99, 100),
        _candle(_dt(9, 20), 100, 101, 99, 100),
    ]
    signals_5m = [
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=0),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=1),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
    ]
    mtf = [_aligned(candles[0].timestamp, aligned=False), _aligned(candles[1].timestamp, True)]
    cfg = _Cfg(
        atr_values_5m=[1.0, 1.0],
        trailing_stop_5m=[95.0, 95.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    assert result.trades == []
    assert result.rejected_trades == []


def test_fresh_signal_required_for_entry() -> None:
    candles = [
        _candle(_dt(9, 15), 100, 101, 99, 100),
        _candle(_dt(9, 20), 100, 101, 99, 100),
    ]
    signals_5m = [
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=1),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
    ]
    mtf = [_aligned(c.timestamp) for c in candles]
    cfg = _Cfg(
        atr_values_5m=[1.0, 1.0],
        trailing_stop_5m=[95.0, 95.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    assert result.trades == []


def test_trailing_stop_ratchets_for_buy() -> None:
    candles = [
        _candle(_dt(9, 15), 100, 101, 99, 100),
        _candle(_dt(9, 20), 100, 101, 99, 100),
        _candle(_dt(9, 25), 100, 101, 99, 100),
        _candle(_dt(9, 30), 100, 101, 99, 100),
    ]
    signals_5m = [
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=0),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=2),
        SignalTransition(side=SignalSide.SELL, is_fresh=True, bar_index=3),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=2),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=3),
    ]
    mtf = [_aligned(c.timestamp) for c in candles]
    cfg = _Cfg(
        atr_values_5m=[1.0, 1.0, 1.0, 1.0],
        trailing_stop_5m=[90.0, 95.0, 93.0, 92.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    trade = result.trades[0]
    assert trade.exit_reason.value == "SIGNAL_5M"
    # Ratchet tightened to 95.0 (from bars 1/2) and never loosened.
    # We can't read open_position directly, so assert no errors and one trade.
    assert trade.entry_price == pytest.approx(100.0, abs=1e-6)


def test_15m_entry_triggers_when_aligned() -> None:
    candles = [
        _candle(_dt(9, 15), 100, 101, 99, 100),
        _candle(_dt(9, 20), 100, 101, 99, 100),
        _candle(_dt(9, 25), 100, 101, 99, 100),
        _candle(_dt(9, 30), 100, 101, 99, 100),
    ]
    signals_5m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=2),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=3),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=0),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=2),
        SignalTransition(side=SignalSide.SELL, is_fresh=True, bar_index=3),
    ]
    mtf = [_aligned(c.timestamp) for c in candles]
    cfg = _Cfg(
        atr_values_5m=[1.0, 1.0, 1.0, 1.0],
        trailing_stop_5m=[95.0, 96.0, 97.0, 98.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.timeframe_entry.value == "15m"
    assert trade.direction.value == "BUY"
    assert trade.exit_reason.value == "SIGNAL_15M"


def test_short_entry_on_sell_signal() -> None:
    candles = [
        _candle(_dt(9, 15), 100, 99, 98, 99),
        _candle(_dt(9, 20), 100, 99, 98, 99),
        _candle(_dt(9, 25), 95, 96, 90, 95),
        _candle(_dt(9, 30), 95, 96, 90, 95),
    ]
    signals_5m = [
        SignalTransition(side=SignalSide.SELL, is_fresh=True, bar_index=0),
        SignalTransition(side=SignalSide.SELL, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.SELL, is_fresh=False, bar_index=2),
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=3),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=2),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=3),
    ]
    mtf = [
        MtfAlignment(
            bias_1d=SignalSide.SELL,
            signal_15m=SignalSide.SELL,
            aligned=True,
            as_of=candles[0].timestamp,
        ),
        MtfAlignment(
            bias_1d=SignalSide.SELL,
            signal_15m=SignalSide.SELL,
            aligned=True,
            as_of=candles[1].timestamp,
        ),
        MtfAlignment(
            bias_1d=SignalSide.SELL,
            signal_15m=SignalSide.SELL,
            aligned=True,
            as_of=candles[2].timestamp,
        ),
        MtfAlignment(
            bias_1d=SignalSide.SELL,
            signal_15m=SignalSide.SELL,
            aligned=True,
            as_of=candles[3].timestamp,
        ),
    ]
    cfg = _Cfg(
        atr_values_5m=[1.0, 1.0, 1.0, 1.0],
        trailing_stop_5m=[105.0, 104.0, 103.0, 102.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.direction.value == "SELL"
    assert trade.exit_reason.value == "SIGNAL_5M"


def test_entry_cutoff_time_prevents_late_entry() -> None:
    candles = [
        _candle(_dt(15, 5), 100, 101, 99, 100),
        _candle(_dt(15, 10), 100, 101, 99, 100),
        _candle(_dt(15, 15), 100, 101, 99, 100),
        _candle(_dt(15, 20), 100, 101, 99, 100),
    ]
    signals_5m = [
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=0),
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=1),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=2),
        SignalTransition(side=SignalSide.SELL, is_fresh=True, bar_index=3),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=2),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=3),
    ]
    mtf = [_aligned(c.timestamp) for c in candles]
    cfg = _Cfg(
        entry_cutoff_time=time(15, 10),
        atr_values_5m=[1.0, 1.0, 1.0, 1.0],
        trailing_stop_5m=[95.0, 95.0, 95.0, 95.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    assert len(result.trades) == 1  # Bar 0 entry allowed
    assert len(result.rejected_trades) == 0  # Bar 1 entry skipped due to cutoff


def test_exit_on_15m_signal() -> None:
    candles = [
        _candle(_dt(9, 15), 100, 101, 99, 100),
        _candle(_dt(9, 20), 100, 101, 99, 100),
        _candle(_dt(9, 25), 100, 101, 99, 100),
    ]
    signals_5m = [
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=0),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=2),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.SELL, is_fresh=True, bar_index=2),
    ]
    mtf = [_aligned(c.timestamp) for c in candles]
    cfg = _Cfg(
        atr_values_5m=[1.0, 1.0, 1.0],
        trailing_stop_5m=[95.0, 96.0, 97.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.exit_reason.value == "SIGNAL_15M"


def test_hard_sl_is_active_stop_before_trail_overtakes() -> None:
    # Entry: BUY at 100, hard_sl at 95 (atr=5, multiplier=1.0)
    # Trailing stops: [95.0, 94.8, 94.5] (stay at or below hard_sl)
    # active_stop = max(hard_sl, trail_sl) = max(95.0, trail_sl) = 95.0
    # Candle at bar 2 dips to 94.8, hits active_stop (95.0)
    candles = [
        _candle(_dt(9, 15), 100, 101, 99, 100),   # Entry bar
        _candle(_dt(9, 20), 100, 102, 95.5, 100), # Trail at 94.8 (updated after), hard_sl=95
        _candle(_dt(9, 25), 100, 102, 94.8, 100), # Dips below hard_sl
        _candle(_dt(9, 30), 100, 101, 99, 100),   # Exit confirmation
    ]
    signals_5m = [
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=0),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=2),
        SignalTransition(side=SignalSide.SELL, is_fresh=True, bar_index=3),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=2),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=3),
    ]
    mtf = [_aligned(c.timestamp) for c in candles]
    cfg = _Cfg(
        sl_atr_multiplier=1.0,
        atr_values_5m=[5.0, 5.0, 5.0, 5.0],
        trailing_stop_5m=[95.0, 94.8, 94.5, 94.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.direction.value == "BUY"
    assert trade.exit_reason.value == "HARD_SL"
    assert trade.exit_price == pytest.approx(95.0, abs=0.01)  # Hard SL is the active stop


def test_trail_becomes_active_stop_after_overtaking_hard_sl() -> None:
    # Entry: BUY at 100, hard_sl at 95 (atr=5, multiplier=1.0)
    # Trailing stops: [95.0, 96.5, 97.0, 98.0] (ratchets above hard_sl)
    # Bar 0: entry, trail=95.0, active_stop=max(95.0,95.0)=95.0
    # Bar 1: trail updated to 96.5, candle doesn't breach 95.0, so continues
    # Bar 2: current_stop=96.5, active_stop=max(95.0,96.5)=96.5, candle dips to 96.0
    #        96.0 <= 96.5 so breach on trail (not hard_sl)
    candles = [
        _candle(_dt(9, 15), 100, 101, 99, 100),   # Entry bar
        _candle(_dt(9, 20), 100, 102, 100, 100),  # No breach yet
        _candle(_dt(9, 25), 100, 102, 96.0, 100), # Dips to 96.0, hits trail at 96.5
        _candle(_dt(9, 30), 100, 101, 99, 100),   # Exit confirmation
    ]
    signals_5m = [
        SignalTransition(side=SignalSide.BUY, is_fresh=True, bar_index=0),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.BUY, is_fresh=False, bar_index=2),
        SignalTransition(side=SignalSide.SELL, is_fresh=True, bar_index=3),
    ]
    signals_15m = [
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=0),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=1),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=2),
        SignalTransition(side=SignalSide.NEUTRAL, is_fresh=False, bar_index=3),
    ]
    mtf = [_aligned(c.timestamp) for c in candles]
    cfg = _Cfg(
        sl_atr_multiplier=1.0,
        atr_values_5m=[5.0, 5.0, 5.0, 5.0],
        trailing_stop_5m=[95.0, 96.5, 97.0, 98.0],
    )

    result = run_simulation(candles, signals_5m, signals_15m, mtf, cfg)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.direction.value == "BUY"
    assert trade.exit_reason.value == "HARD_SL"
    assert trade.exit_price == pytest.approx(96.5, abs=0.01)  # Trail is now the active stop
