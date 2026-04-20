"""ATR indicator computation."""

from __future__ import annotations

import math

from src.models.candle import Candle
from src.utils.exceptions import InsufficientDataError


def _first_true_range(candle: Candle) -> float:
    """Compute first-bar true range.

    Args:
        candle: First candle in the series.

    Returns:
        The first-bar true range (high-low).
    """
    return candle.high - candle.low


def _true_range(current: Candle, previous_close: float) -> float:
    """Compute true range for one candle.

    Args:
        current: Current candle.
        previous_close: Previous candle close.

    Returns:
        The true range value.
    """
    range_high_low = current.high - current.low
    range_high_prev_close = abs(current.high - previous_close)
    range_low_prev_close = abs(current.low - previous_close)
    return max(range_high_low, range_high_prev_close, range_low_prev_close)


def compute_atr(candles: list[Candle], period: int) -> list[float]:
    """Compute ATR values using Wilder's smoothing (RMA).

    Args:
        candles: Ordered candle list.
        period: ATR period.

    Returns:
        ATR values with same length as input candles, where warmup values are NaN.

    Raises:
        ValueError: If period is not positive.
        InsufficientDataError: If candles are fewer than period.
    """
    if period <= 0:
        raise ValueError("period must be > 0")
    if len(candles) < period:
        raise InsufficientDataError(
            f"Need at least {period} candles for ATR(period={period})."
        )

    atr_values = [math.nan] * len(candles)
    tr_values = [_first_true_range(candles[0])]

    for idx in range(1, len(candles)):
        tr_values.append(_true_range(candles[idx], candles[idx - 1].close))

    first_atr = sum(tr_values[:period]) / period
    atr_values[period - 1] = first_atr

    previous_atr = first_atr
    for idx in range(period, len(candles)):
        current_tr = tr_values[idx]
        previous_atr = ((previous_atr * (period - 1)) + current_tr) / period
        atr_values[idx] = previous_atr

    return atr_values
