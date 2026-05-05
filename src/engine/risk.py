"""Risk sizing and stop-loss helpers.

This module contains pure functions for computing position size and hard stop
levels. It intentionally does not depend on configuration objects.
"""

from __future__ import annotations

import math

from src.utils.enums import SignalSide


def compute_position_size(
    capital: float,
    risk_pct: float,
    entry_price: float,
    hard_sl_price: float,
) -> int:
    """Compute position quantity using fixed-fractional risk sizing.

    The sizing model risks ``capital * risk_pct`` rupees on the distance between
    the entry price and the hard stop price.

    Args:
        capital: Available capital in rupees.
        risk_pct: Fraction of capital to risk (e.g. 0.01 for 1%).
        entry_price: Intended entry price.
        hard_sl_price: Hard stop-loss price.

    Returns:
        The computed quantity (may be 0 when the risk amount is smaller than
        the cost of a single share's SL distance — callers must reject trades
        with quantity == 0 and log them).

    Raises:
        ValueError: If ``capital <= 0`` or ``risk_pct <= 0``.
        ValueError: If stop-loss distance is non-positive.
    """
    if capital <= 0:
        raise ValueError("capital must be > 0")
    if risk_pct <= 0:
        raise ValueError("risk_pct must be > 0")

    sl_distance = abs(entry_price - hard_sl_price)
    if sl_distance <= 0:
        raise ValueError("sl_distance must be > 0")

    risk_amount = capital * risk_pct
    raw_qty = risk_amount / sl_distance
    return math.floor(raw_qty)


def compute_hard_sl(
    entry_price: float,
    direction: SignalSide,
    atr: float,
    sl_atr_multiplier: float,
) -> float:
    """Compute hard stop-loss price from ATR.

    Args:
        entry_price: Entry price.
        direction: Trade direction (BUY for long, SELL for short).
        atr: Average True Range value.
        sl_atr_multiplier: Multiplier applied to ATR.

    Returns:
        Hard stop-loss price.

    Raises:
        ValueError: If ``atr <= 0``.
        ValueError: If ``sl_atr_multiplier <= 0``.
    """
    if atr <= 0:
        raise ValueError("atr must be > 0")
    if sl_atr_multiplier <= 0:
        raise ValueError("sl_atr_multiplier must be > 0")

    direction = SignalSide(direction)
    offset = atr * sl_atr_multiplier
    if direction == SignalSide.BUY:
        return entry_price - offset
    if direction == SignalSide.SELL:
        return entry_price + offset
    raise ValueError("direction must be BUY or SELL")

