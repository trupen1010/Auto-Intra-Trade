"""Datetime helper utilities for the backtest engine.

All public helpers in this module operate with timezone-aware datetimes and
normalize to Asia/Kolkata to avoid implicit timezone bugs.
"""

from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from src.utils.enums import Timeframe

IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(hour=9, minute=15)
MARKET_CLOSE = time(hour=15, minute=30)


def validate_ist_datetime(dt: datetime, field_name: str = "datetime") -> None:
    """Validate that a datetime is timezone-aware and in Asia/Kolkata.

    Args:
        dt: Datetime to validate.
        field_name: Field name used for error messages.

    Raises:
        ValueError: If datetime is timezone-naive or not Asia/Kolkata.
    """
    if dt.tzinfo is None:
        msg = f"{field_name} must be timezone-aware Asia/Kolkata datetime."
        raise ValueError(msg)

    if getattr(dt.tzinfo, "key", None) != IST.key:
        msg = f"{field_name} must be timezone-aware Asia/Kolkata datetime."
        raise ValueError(msg)


def to_ist(dt: datetime) -> datetime:
    """Convert a timezone-aware datetime to Asia/Kolkata.

    Args:
        dt: Source timezone-aware datetime.

    Returns:
        Datetime converted to Asia/Kolkata timezone.

    Raises:
        ValueError: If the input datetime is timezone-naive.
    """
    if dt.tzinfo is None:
        msg = "Datetime must be timezone-aware."
        raise ValueError(msg)

    return dt.astimezone(IST)


def is_market_hours(dt: datetime) -> bool:
    """Check if a timestamp is within Indian market hours.

    Market hours are 09:15 to 15:30 IST, inclusive.

    Args:
        dt: Timezone-aware datetime.

    Returns:
        True when the IST local time is within market hours, else False.
    """
    ist_dt = to_ist(dt)
    current_time = ist_dt.time()
    return MARKET_OPEN <= current_time <= MARKET_CLOSE


def is_same_session(dt1: datetime, dt2: datetime) -> bool:
    """Check whether two timestamps belong to the same IST session date.

    Args:
        dt1: First timezone-aware datetime.
        dt2: Second timezone-aware datetime.

    Returns:
        True when both timestamps map to the same IST calendar date.
    """
    return to_ist(dt1).date() == to_ist(dt2).date()


def candle_close_time(open_time: datetime, timeframe: str) -> datetime:
    """Compute candle close time for a given open timestamp and timeframe.

    Args:
        open_time: Timezone-aware candle open timestamp.
        timeframe: One of "5m", "15m", or "1d".

    Returns:
        Timezone-aware candle close timestamp in IST.

    Raises:
        ValueError: If the open timestamp is timezone-naive.
        ValueError: If the timeframe is unsupported.
    """
    ist_open = to_ist(open_time)

    if timeframe == Timeframe.FIVE_MINUTE.value:
        return ist_open + timedelta(minutes=5)

    if timeframe == Timeframe.FIFTEEN_MINUTE.value:
        return ist_open + timedelta(minutes=15)

    if timeframe == Timeframe.ONE_DAY.value:
        return datetime.combine(ist_open.date(), MARKET_CLOSE, tzinfo=IST)

    msg = f"Unsupported timeframe: {timeframe}"
    raise ValueError(msg)
