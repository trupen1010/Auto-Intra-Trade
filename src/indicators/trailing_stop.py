"""ATR trailing-stop computation."""

from __future__ import annotations

import math

from src.models.candle import Candle
from src.utils.enums import SignalSide


def compute_trailing_stop(
    candles: list[Candle],
    atr_values: list[float],
    sensitivity: int,
) -> tuple[list[float], list[SignalSide]]:
    """Compute recursive ATR trailing stop from candles and ATR values.

    Args:
        candles: Ordered candle list.
        atr_values: Precomputed ATR values aligned with candles.
        sensitivity: Multiplication factor for ATR loss distance.

    Returns:
        A tuple of trailing-stop values and per-bar signal side states.

    Raises:
        ValueError: If candle and ATR lengths differ.
    """
    if len(candles) != len(atr_values):
        raise ValueError("candles and atr_values must have the same length")
    if not candles:
        return ([], [])

    stops = [0.0] * len(candles)
    positions = [0] * len(candles)
    sides = [SignalSide.NEUTRAL] * len(candles)

    for idx in range(1, len(candles)):
        close = candles[idx].close
        prev_close = candles[idx - 1].close
        prev_stop = stops[idx - 1]
        atr_value = atr_values[idx]

        if not math.isfinite(atr_value):
            stops[idx] = prev_stop
            positions[idx] = positions[idx - 1]
            sides[idx] = sides[idx - 1]
            continue

        loss = float(sensitivity) * atr_value

        if close > prev_stop and prev_close > prev_stop:
            stops[idx] = max(prev_stop, close - loss)
        elif close < prev_stop and prev_close < prev_stop:
            stops[idx] = min(prev_stop, close + loss)
        elif close > prev_stop:
            stops[idx] = close - loss
        else:
            stops[idx] = close + loss

        if prev_close > prev_stop and close < prev_stop:
            positions[idx] = -1
        elif prev_close < prev_stop and close > prev_stop:
            positions[idx] = 1
        else:
            positions[idx] = positions[idx - 1]

        if positions[idx] == 1:
            sides[idx] = SignalSide.BUY
        elif positions[idx] == -1:
            sides[idx] = SignalSide.SELL
        else:
            sides[idx] = SignalSide.NEUTRAL

    return (stops, sides)
