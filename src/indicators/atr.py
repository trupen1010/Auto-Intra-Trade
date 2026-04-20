"""ATR indicator computation."""

from __future__ import annotations

from src.models.candle import Candle
from src.utils.exceptions import InsufficientDataError


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
        ATR values with same length as input candles, where warmup values are 0.0.

    Raises:
        ValueError: If period is not positive.
        InsufficientDataError: If candles are fewer than period + 1.
    """
    if period <= 0:
        raise ValueError("period must be > 0")
    if len(candles) < period + 1:
        raise InsufficientDataError(
            f"Need at least {period + 1} candles for ATR(period={period})."
        )

    atr_values = [0.0] * len(candles)
    tr_values: list[float] = []

    for idx in range(1, len(candles)):
        tr_values.append(_true_range(candles[idx], candles[idx - 1].close))

    first_atr = sum(tr_values[:period]) / period
    atr_values[period] = first_atr

    previous_atr = first_atr
    for idx in range(period + 1, len(candles)):
        current_tr = tr_values[idx - 1]
        previous_atr = ((previous_atr * (period - 1)) + current_tr) / period
        atr_values[idx] = previous_atr

    return atr_values

