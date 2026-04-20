"""ATR trailing-stop computation."""

from __future__ import annotations

from src.models.candle import Candle


def compute_trailing_stop(
    candles: list[Candle],
    atr_values: list[float],
    sensitivity: int,
) -> list[float]:
    """Compute recursive ATR trailing stop from candles and ATR values.

    Args:
        candles: Ordered candle list.
        atr_values: Precomputed ATR values aligned with candles.
        sensitivity: Multiplication factor for ATR loss distance.

    Returns:
        Trailing-stop values with same length as candles.

    Raises:
        ValueError: If candle and ATR lengths differ.
    """
    if len(candles) != len(atr_values):
        raise ValueError("candles and atr_values must have the same length")
    if not candles:
        return []

    stops = [0.0] * len(candles)

    for idx in range(1, len(candles)):
        close = candles[idx].close
        prev_close = candles[idx - 1].close
        prev_stop = stops[idx - 1]
        loss = float(sensitivity) * atr_values[idx]

        if close > prev_stop and prev_close > prev_stop:
            stops[idx] = max(prev_stop, close - loss)
        elif close < prev_stop and prev_close < prev_stop:
            stops[idx] = min(prev_stop, close + loss)
        elif close > prev_stop:
            stops[idx] = close - loss
        else:
            stops[idx] = close + loss

    return stops

