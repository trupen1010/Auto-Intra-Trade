from __future__ import annotations

import pytest
from datetime import datetime
from zoneinfo import ZoneInfo

from src.indicators.mtf_state import resolve_mtf_alignment
from src.models.candle import Candle
from src.models.signal_state import SignalTransition
from src.utils.enums import SignalSide


IST = ZoneInfo("Asia/Kolkata")


def _candle(ts: datetime, *, timeframe: str) -> Candle:
    return Candle(
        symbol="TEST",
        timeframe=timeframe,
        timestamp=ts,
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1.0,
    )


def _t(side: SignalSide, bar_index: int) -> SignalTransition:
    return SignalTransition(side=side, is_fresh=True, bar_index=bar_index)


def test_aligned_when_1d_and_15m_both_buy() -> None:
    ts_5m = datetime(2024, 1, 2, 9, 20, tzinfo=IST)

    candles_1d = [_candle(datetime(2024, 1, 1, 15, 30, tzinfo=IST), timeframe="1d")]
    signals_1d = [_t(SignalSide.BUY, 0)]

    # 15m open 09:05 → close 09:20 == ts_5m; inclusive boundary includes it.
    candles_15m = [_candle(datetime(2024, 1, 2, 9, 5, tzinfo=IST), timeframe="15m")]
    signals_15m = [_t(SignalSide.BUY, 0)]

    alignment = resolve_mtf_alignment(ts_5m, signals_1d, signals_15m, candles_1d, candles_15m)
    assert alignment.bias_1d == SignalSide.BUY
    assert alignment.signal_15m == SignalSide.BUY
    assert alignment.aligned is True
    assert alignment.as_of == ts_5m


def test_not_aligned_when_sides_differ() -> None:
    ts_5m = datetime(2024, 1, 2, 9, 20, tzinfo=IST)

    candles_1d = [_candle(datetime(2024, 1, 1, 15, 30, tzinfo=IST), timeframe="1d")]
    signals_1d = [_t(SignalSide.BUY, 0)]

    # 15m open 09:05 → close 09:20 == ts_5m; inclusive boundary includes it.
    candles_15m = [_candle(datetime(2024, 1, 2, 9, 5, tzinfo=IST), timeframe="15m")]
    signals_15m = [_t(SignalSide.SELL, 0)]

    alignment = resolve_mtf_alignment(ts_5m, signals_1d, signals_15m, candles_1d, candles_15m)
    assert alignment.aligned is False


def test_not_aligned_when_either_is_neutral() -> None:
    ts_5m = datetime(2024, 1, 2, 9, 20, tzinfo=IST)

    candles_1d = [_candle(datetime(2024, 1, 1, 15, 30, tzinfo=IST), timeframe="1d")]
    signals_1d = [_t(SignalSide.NEUTRAL, 0)]

    # 15m open 09:05 → close 09:20 == ts_5m; inclusive boundary includes it.
    candles_15m = [_candle(datetime(2024, 1, 2, 9, 5, tzinfo=IST), timeframe="15m")]
    signals_15m = [_t(SignalSide.BUY, 0)]

    alignment = resolve_mtf_alignment(ts_5m, signals_1d, signals_15m, candles_1d, candles_15m)
    assert alignment.bias_1d == SignalSide.NEUTRAL
    assert alignment.aligned is False


def test_no_lookahead_close_time_boundary() -> None:
    """Candle whose close_time == ts_5m is included; close_time > ts_5m is excluded."""
    ts_5m = datetime(2024, 1, 2, 9, 20, tzinfo=IST)

    candles_1d = [_candle(datetime(2024, 1, 1, 15, 30, tzinfo=IST), timeframe="1d")]
    signals_1d = [_t(SignalSide.BUY, 0)]

    candles_15m = [
        # open 09:05 → close 09:20 == ts_5m → included (BUY)
        _candle(datetime(2024, 1, 2, 9, 5, tzinfo=IST), timeframe="15m"),
        # open 09:20 → close 09:35 > ts_5m → excluded (SELL)
        _candle(datetime(2024, 1, 2, 9, 20, tzinfo=IST), timeframe="15m"),
    ]
    signals_15m = [_t(SignalSide.BUY, 0), _t(SignalSide.SELL, 1)]

    alignment = resolve_mtf_alignment(ts_5m, signals_1d, signals_15m, candles_1d, candles_15m)
    # The 09:05 candle (close == ts_5m) is included; SELL candle is excluded.
    assert alignment.signal_15m == SignalSide.BUY
    assert alignment.aligned is True


def test_returns_neutral_when_no_prior_signals_exist() -> None:
    ts_5m = datetime(2024, 1, 2, 9, 20, tzinfo=IST)

    # 1D candle for the same day: close = 15:30 > 09:20 → excluded
    candles_1d = [_candle(datetime(2024, 1, 2, 15, 30, tzinfo=IST), timeframe="1d")]
    signals_1d = [_t(SignalSide.BUY, 0)]

    # 15m candle open 09:20 → close 09:35 > ts_5m → excluded
    candles_15m = [_candle(datetime(2024, 1, 2, 9, 20, tzinfo=IST), timeframe="15m")]
    signals_15m = [_t(SignalSide.SELL, 0)]

    alignment = resolve_mtf_alignment(ts_5m, signals_1d, signals_15m, candles_1d, candles_15m)
    assert alignment.bias_1d == SignalSide.NEUTRAL
    assert alignment.signal_15m == SignalSide.NEUTRAL
    assert alignment.aligned is False


def test_raises_on_length_mismatch() -> None:
    ts_5m = datetime(2024, 1, 2, 9, 20, tzinfo=IST)

    candles_1d = [_candle(datetime(2024, 1, 1, 15, 30, tzinfo=IST), timeframe="1d")]
    # Two signals but only one candle → mismatch
    signals_1d = [_t(SignalSide.BUY, 0), _t(SignalSide.BUY, 1)]

    candles_15m: list[Candle] = []
    signals_15m: list[SignalTransition] = []

    with pytest.raises(ValueError, match="signals_1d length must match candles_1d"):
        resolve_mtf_alignment(ts_5m, signals_1d, signals_15m, candles_1d, candles_15m)

