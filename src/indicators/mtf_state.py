"""Multi-timeframe state resolver.

This module resolves higher-timeframe bias/signal states as-of a 5m timestamp
without lookahead.
"""

from __future__ import annotations

from datetime import datetime

from src.models.candle import Candle
from src.models.mtf_alignment import MtfAlignment
from src.models.signal_state import SignalTransition
from src.utils.datetime_utils import candle_close_time, validate_ist_datetime
from src.utils.enums import SignalSide


def resolve_mtf_alignment(
    ts_5m: datetime,
    signals_1d: list[SignalTransition],
    signals_15m: list[SignalTransition],
    candles_1d: list[Candle],
    candles_15m: list[Candle],
) -> MtfAlignment:
    """Resolve 1D/15m alignment as of an open 5m bar.

    Anti-lookahead rule:
        Only use higher-timeframe candles and transitions where the candle's
        *close* time is less than or equal to the provided 5m timestamp
        (``candle_close_time(candle) <= ts_5m``). A bar is eligible only
        after it is fully closed; same-close-time bars are included (inclusive
        boundary).

    Args:
        ts_5m: Timestamp of the currently open 5m bar.
        signals_1d: Signal transitions aligned by index with candles_1d.
        signals_15m: Signal transitions aligned by index with candles_15m.
        candles_1d: Closed 1D candles.
        candles_15m: Closed 15m candles.

    Returns:
        Alignment summary for 1D bias and 15m signal as of ts_5m.

    Raises:
        ValueError: If inputs are not aligned by length or timestamp invalid.
    """

    validate_ist_datetime(ts_5m, "ts_5m")

    if len(signals_1d) != len(candles_1d):
        raise ValueError("signals_1d length must match candles_1d")
    if len(signals_15m) != len(candles_15m):
        raise ValueError("signals_15m length must match candles_15m")

    bias_1d = _latest_side_before(ts_5m, candles_1d, signals_1d)
    signal_15m = _latest_side_before(ts_5m, candles_15m, signals_15m)

    aligned = (
        bias_1d != SignalSide.NEUTRAL
        and signal_15m != SignalSide.NEUTRAL
        and bias_1d == signal_15m
    )

    return MtfAlignment(
        bias_1d=bias_1d,
        signal_15m=signal_15m,
        aligned=aligned,
        as_of=ts_5m,
    )


def _latest_side_before(
    as_of: datetime,
    candles: list[Candle],
    transitions: list[SignalTransition],
) -> SignalSide:
    latest_side = SignalSide.NEUTRAL

    for candle, transition in zip(candles, transitions, strict=True):
        if candle_close_time(candle.timestamp, candle.timeframe) > as_of:
            break
        latest_side = transition.side

    return latest_side

