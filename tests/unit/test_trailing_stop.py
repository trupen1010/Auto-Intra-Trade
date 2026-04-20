"""Unit tests for ATR trailing stop computation."""

from __future__ import annotations

from datetime import datetime, timedelta
import math
from zoneinfo import ZoneInfo

import pytest

from src.indicators.trailing_stop import compute_trailing_stop
from src.models.candle import Candle
from src.utils.enums import SignalSide

IST = ZoneInfo("Asia/Kolkata")


def _build_candle_series(closes: list[float]) -> list[Candle]:
    """Create deterministic candles from close prices.

    Args:
        closes: Ordered close prices.

    Returns:
        Ordered candle list.
    """
    base_ts = datetime(2026, 4, 20, 9, 15, tzinfo=IST)
    candles: list[Candle] = []
    for idx, close in enumerate(closes):
        candles.append(
            Candle(
                symbol="RELIANCE",
                timeframe="5m",
                timestamp=base_ts + timedelta(minutes=5 * idx),
                open=close - 0.5,
                high=close + 0.5,
                low=close - 1.0,
                close=close,
                volume=1000.0 + idx,
            )
        )
    return candles


def test_trailing_stop_bullish_ratchet() -> None:
    """In bullish sequence, stop ratchets upward and does not decrease."""
    candles = _build_candle_series([100.0, 102.0, 104.0, 106.0, 108.0])
    atr_values = [0.0, 1.0, 1.0, 1.0, 1.0]

    stops, sides = compute_trailing_stop(candles, atr_values, sensitivity=2)

    assert stops[0] == 0.0
    assert stops == [0.0, 100.0, 102.0, 104.0, 106.0]
    assert all(curr >= prev for prev, curr in zip(stops[1:-1], stops[2:]))
    assert all(side == SignalSide.NEUTRAL for side in sides)


def test_trailing_stop_bearish_ratchet() -> None:
    """In bearish sequence, stop ratchets downward and does not increase."""
    candles = _build_candle_series([100.0, 102.0, 80.0, 78.0, 76.0])
    atr_values = [0.0, 1.0, 1.0, 1.0, 1.0]

    stops, _ = compute_trailing_stop(candles, atr_values, sensitivity=2)

    assert stops[0] == 0.0
    assert stops == [0.0, 100.0, 82.0, 80.0, 78.0]
    assert all(curr <= prev for prev, curr in zip(stops[2:-1], stops[3:]))


def test_trailing_stop_raises_on_length_mismatch() -> None:
    """Trailing stop raises when candles and ATR lengths differ."""
    candles = _build_candle_series([100.0, 101.0, 102.0])

    with pytest.raises(ValueError, match="same length"):
        compute_trailing_stop(candles, [0.0, 1.0], sensitivity=3)


def test_trailing_stop_first_value_is_zero() -> None:
    """Trailing stop index 0 is always 0.0 due to missing prior state."""
    candles = _build_candle_series([100.0, 102.0, 104.0])
    atr_values = [0.0, 1.0, 1.0]

    stops, _ = compute_trailing_stop(candles, atr_values, sensitivity=3)

    assert stops[0] == 0.0


def test_trailing_stop_preserves_previous_stop_for_nan_atr() -> None:
    """Warmup/non-finite ATR keeps stop state unchanged."""
    candles = _build_candle_series([100.0, 102.0, 104.0, 106.0])
    atr_values = [math.nan, math.nan, 1.0, 1.0]

    stops, sides = compute_trailing_stop(candles, atr_values, sensitivity=2)

    assert stops[:2] == [0.0, 0.0]
    assert stops[2:] == [102.0, 104.0]
    assert sides[1] == SignalSide.NEUTRAL


def test_trailing_stop_handles_direction_flip() -> None:
    """Trailing-stop recursion handles bearish then bullish flip correctly."""
    candles = _build_candle_series([100.0, 102.0, 80.0, 85.0])
    atr_values = [0.0, 1.0, 1.0, 1.0]

    stops, sides = compute_trailing_stop(candles, atr_values, sensitivity=2)

    assert stops == [0.0, 100.0, 82.0, 83.0]
    assert sides[2] == SignalSide.SELL
    assert sides[3] == SignalSide.BUY
