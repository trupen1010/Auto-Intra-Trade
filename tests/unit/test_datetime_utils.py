"""Unit tests for datetime utilities."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.utils.datetime_utils import candle_close_time, is_market_hours, is_same_session, to_ist

UTC = ZoneInfo("UTC")
IST = ZoneInfo("Asia/Kolkata")


def test_to_ist_converts_utc_correctly() -> None:
    """to_ist converts a UTC timestamp to the expected IST timestamp."""
    utc_time = datetime(2026, 4, 19, 3, 45, tzinfo=UTC)

    result = to_ist(utc_time)

    assert result == datetime(2026, 4, 19, 9, 15, tzinfo=IST)


def test_is_market_hours_boundaries() -> None:
    """is_market_hours enforces inclusive open and close boundaries."""
    at_open = datetime(2026, 4, 19, 9, 15, tzinfo=IST)
    before_open = datetime(2026, 4, 19, 9, 14, tzinfo=IST)
    after_close = datetime(2026, 4, 19, 15, 31, tzinfo=IST)

    assert is_market_hours(at_open) is True
    assert is_market_hours(before_open) is False
    assert is_market_hours(after_close) is False


def test_is_same_session_false_across_midnight() -> None:
    """is_same_session returns False when timestamps cross IST midnight."""
    session_end = datetime(2026, 4, 19, 23, 59, tzinfo=IST)
    next_day = datetime(2026, 4, 20, 0, 0, tzinfo=IST)

    assert is_same_session(session_end, next_day) is False


def test_candle_close_time_for_supported_timeframes() -> None:
    """candle_close_time returns expected closes for 5m, 15m, and 1d."""
    open_time = datetime(2026, 4, 19, 9, 15, tzinfo=IST)

    close_5m = candle_close_time(open_time, "5m")
    close_15m = candle_close_time(open_time, "15m")
    close_1d = candle_close_time(open_time, "1d")

    assert close_5m == datetime(2026, 4, 19, 9, 20, tzinfo=IST)
    assert close_15m == datetime(2026, 4, 19, 9, 30, tzinfo=IST)
    assert close_1d == datetime(2026, 4, 19, 15, 30, tzinfo=IST)
