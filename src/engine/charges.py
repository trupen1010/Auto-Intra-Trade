"""Charges computation.

This module contains a pure function for computing round-trip charges.
All configuration (rates) must be provided as explicit parameters.
"""

from __future__ import annotations


def calculate_round_trip_charges(
    entry_price: float,
    exit_price: float,
    quantity: int,
    brokerage_pct: float,
    stt_pct: float,
    exchange_pct: float,
    sebi_pct: float,
    gst_pct: float,
    stamp_pct: float,
) -> float:
    """Calculate total round-trip charges for a trade.

    Args:
        entry_price: Executed entry price.
        exit_price: Executed exit price.
        quantity: Filled quantity.
        brokerage_pct: Brokerage rate applied to total turnover.
        stt_pct: Securities Transaction Tax rate (sell-side turnover only).
        exchange_pct: Exchange transaction charges rate.
        sebi_pct: SEBI charges rate.
        gst_pct: GST rate applied to brokerage + exchange charges.
        stamp_pct: Stamp duty rate (buy-side turnover only).

    Returns:
        Total charges for the round trip.

    Raises:
        ValueError: If any provided parameter is negative.
    """
    params = {
        "entry_price": entry_price,
        "exit_price": exit_price,
        "quantity": float(quantity),
        "brokerage_pct": brokerage_pct,
        "stt_pct": stt_pct,
        "exchange_pct": exchange_pct,
        "sebi_pct": sebi_pct,
        "gst_pct": gst_pct,
        "stamp_pct": stamp_pct,
    }
    for name, value in params.items():
        if value < 0:
            raise ValueError(f"{name} must be >= 0")

    entry_notional = entry_price * float(quantity)
    exit_notional = exit_price * float(quantity)
    turnover = entry_notional + exit_notional

    brokerage = turnover * brokerage_pct
    stt = exit_notional * stt_pct
    exchange = turnover * exchange_pct
    sebi = turnover * sebi_pct
    gst = (brokerage + exchange) * gst_pct
    stamp = entry_notional * stamp_pct

    return brokerage + stt + exchange + sebi + gst + stamp

