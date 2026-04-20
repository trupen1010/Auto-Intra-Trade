"""Unit tests for ATR computation."""

from __future__ import annotations

from datetime import datetime, timedelta
import math
from zoneinfo import ZoneInfo

import pytest

from src.indicators.atr import compute_atr
from src.models.candle import Candle
from src.utils.exceptions import InsufficientDataError

IST = ZoneInfo("Asia/Kolkata")


def _build_candle_series(prices: list[tuple[float, float, float, float]]) -> list[Candle]:
    """Create deterministic candles for tests.

    Args:
        prices: Tuple list of (open, high, low, close).

    Returns:
        Ordered candle list.
    """
    base_ts = datetime(2026, 4, 20, 9, 15, tzinfo=IST)
    candles: list[Candle] = []
    for idx, (open_, high, low, close) in enumerate(prices):
        candles.append(
            Candle(
                symbol="RELIANCE",
                timeframe="5m",
                timestamp=base_ts + timedelta(minutes=5 * idx),
                open=open_,
                high=high,
                low=low,
                close=close,
                volume=1000.0 + idx,
            )
        )
    return candles


def test_atr_wilder_smoothing_matches_known_values() -> None:
    """ATR uses Wilder smoothing and matches known deterministic output."""
    candles = _build_candle_series(
        [
            (10.0, 11.0, 9.0, 10.0),
            (10.0, 12.0, 10.0, 11.0),
            (11.0, 13.0, 10.0, 12.0),
            (12.0, 14.0, 11.0, 13.0),
            (13.0, 15.0, 12.0, 14.0),
        ]
    )

    atr = compute_atr(candles, period=3)

    assert math.isnan(atr[0])
    assert math.isnan(atr[1])
    assert [round(value, 4) for value in atr[2:]] == [2.3333, 2.5556, 2.7037]


def test_atr_returns_nan_for_warmup_period() -> None:
    """ATR warmup window remains NaN for first period - 1 values."""
    candles = _build_candle_series(
        [
            (100.0, 101.0, 99.0, 100.0),
            (100.0, 102.0, 99.0, 101.0),
            (101.0, 103.0, 100.0, 102.0),
            (102.0, 104.0, 101.0, 103.0),
        ]
    )

    atr = compute_atr(candles, period=3)

    assert math.isnan(atr[0])
    assert math.isnan(atr[1])
    assert not math.isnan(atr[2])


def test_atr_raises_insufficient_data_if_too_few_candles() -> None:
    """ATR raises InsufficientDataError for fewer than period candles."""
    candles = _build_candle_series(
        [
            (100.0, 101.0, 99.0, 100.0),
            (100.0, 102.0, 99.0, 101.0),
        ]
    )

    with pytest.raises(InsufficientDataError):
        compute_atr(candles, period=3)


def test_atr_output_length_matches_input() -> None:
    """ATR output list length always matches candle input length."""
    candles = _build_candle_series(
        [
            (10.0, 11.0, 9.0, 10.0),
            (10.0, 12.0, 10.0, 11.0),
            (11.0, 13.0, 10.0, 12.0),
            (12.0, 14.0, 11.0, 13.0),
            (13.0, 15.0, 12.0, 14.0),
        ]
    )

    atr = compute_atr(candles, period=3)

    assert len(atr) == len(candles)


def test_atr_raises_value_error_for_non_positive_period() -> None:
    """ATR rejects zero and negative period values."""
    candles = _build_candle_series(
        [
            (10.0, 11.0, 9.0, 10.0),
            (10.0, 12.0, 10.0, 11.0),
            (11.0, 13.0, 10.0, 12.0),
            (12.0, 14.0, 11.0, 13.0),
            (13.0, 15.0, 12.0, 14.0),
        ]
    )

    with pytest.raises(ValueError):
        compute_atr(candles, period=0)

    with pytest.raises(ValueError):
        compute_atr(candles, period=-1)
