from __future__ import annotations

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

    candles_15m = [_candle(datetime(2024, 1, 2, 9, 15, tzinfo=IST), timeframe="15m")]
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

    candles_15m = [_candle(datetime(2024, 1, 2, 9, 15, tzinfo=IST), timeframe="15m")]
    signals_15m = [_t(SignalSide.SELL, 0)]

    alignment = resolve_mtf_alignment(ts_5m, signals_1d, signals_15m, candles_1d, candles_15m)
    assert alignment.aligned is False


def test_not_aligned_when_either_is_neutral() -> None:
    ts_5m = datetime(2024, 1, 2, 9, 20, tzinfo=IST)

    candles_1d = [_candle(datetime(2024, 1, 1, 15, 30, tzinfo=IST), timeframe="1d")]
    signals_1d = [_t(SignalSide.NEUTRAL, 0)]

    candles_15m = [_candle(datetime(2024, 1, 2, 9, 15, tzinfo=IST), timeframe="15m")]
    signals_15m = [_t(SignalSide.BUY, 0)]

    alignment = resolve_mtf_alignment(ts_5m, signals_1d, signals_15m, candles_1d, candles_15m)
    assert alignment.bias_1d == SignalSide.NEUTRAL
    assert alignment.aligned is False


def test_no_lookahead_excludes_same_timestamp_candles() -> None:
    ts_5m = datetime(2024, 1, 2, 9, 20, tzinfo=IST)

    candles_1d = [_candle(datetime(2024, 1, 1, 15, 30, tzinfo=IST), timeframe="1d")]
    signals_1d = [_t(SignalSide.BUY, 0)]

    candles_15m = [
        _candle(datetime(2024, 1, 2, 9, 5, tzinfo=IST), timeframe="15m"),
        _candle(datetime(2024, 1, 2, 9, 20, tzinfo=IST), timeframe="15m"),
    ]
    signals_15m = [_t(SignalSide.BUY, 0), _t(SignalSide.SELL, 1)]

    alignment = resolve_mtf_alignment(ts_5m, signals_1d, signals_15m, candles_1d, candles_15m)
    assert alignment.signal_15m == SignalSide.BUY
    assert alignment.aligned is True


def test_returns_neutral_when_no_prior_signals_exist() -> None:
    ts_5m = datetime(2024, 1, 2, 9, 20, tzinfo=IST)

    candles_1d = [_candle(datetime(2024, 1, 2, 15, 30, tzinfo=IST), timeframe="1d")]
    signals_1d = [_t(SignalSide.BUY, 0)]

    candles_15m = [_candle(datetime(2024, 1, 2, 9, 20, tzinfo=IST), timeframe="15m")]
    signals_15m = [_t(SignalSide.SELL, 0)]

    alignment = resolve_mtf_alignment(ts_5m, signals_1d, signals_15m, candles_1d, candles_15m)
    assert alignment.bias_1d == SignalSide.NEUTRAL
    assert alignment.signal_15m == SignalSide.NEUTRAL
    assert alignment.aligned is False

