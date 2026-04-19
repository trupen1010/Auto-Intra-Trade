"""Unit tests for candle sequence validator."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.data.validator import validate_candle_sequence
from src.models.candle import Candle
from src.utils.exceptions import DataGapError, InsufficientDataError, InvalidCandleError

IST = ZoneInfo("Asia/Kolkata")


def _candle(
    timestamp: datetime,
    timeframe: str = "5m",
    symbol: str = "NSE_EQ|INE002A01018",
) -> Candle:
    """Build a minimal valid candle for validator tests."""
    return Candle(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        open=100.0,
        high=101.0,
        low=99.5,
        close=100.5,
        volume=1000.0,
    )


def test_validate_raises_insufficient_data_if_less_than_2_candles() -> None:
    """Validator requires at least two candles."""
    candles = [_candle(datetime(2026, 4, 19, 9, 20, tzinfo=IST))]

    with pytest.raises(InsufficientDataError):
        validate_candle_sequence(candles, timeframe="5m", symbol="NSE_EQ|INE002A01018")


def test_validate_raises_on_out_of_order_candles() -> None:
    """Validator rejects sequences with descending timestamps."""
    candles = [
        _candle(datetime(2026, 4, 19, 9, 25, tzinfo=IST)),
        _candle(datetime(2026, 4, 19, 9, 20, tzinfo=IST)),
    ]

    with pytest.raises(InvalidCandleError, match="Out-of-order"):
        validate_candle_sequence(candles, timeframe="5m", symbol="NSE_EQ|INE002A01018")


def test_validate_raises_on_duplicate_timestamps() -> None:
    """Validator rejects duplicate candle timestamps."""
    duplicate_ts = datetime(2026, 4, 19, 9, 20, tzinfo=IST)
    candles = [_candle(duplicate_ts), _candle(duplicate_ts)]

    with pytest.raises(InvalidCandleError, match="Duplicate"):
        validate_candle_sequence(candles, timeframe="5m", symbol="NSE_EQ|INE002A01018")


def test_validate_raises_outside_market_hours_for_intraday() -> None:
    """Intraday candles outside market hours are rejected."""
    candles = [
        _candle(datetime(2026, 4, 19, 9, 10, tzinfo=IST)),
        _candle(datetime(2026, 4, 19, 9, 15, tzinfo=IST)),
    ]

    with pytest.raises(InvalidCandleError, match="outside market hours"):
        validate_candle_sequence(candles, timeframe="5m", symbol="NSE_EQ|INE002A01018")


def test_validate_skips_market_hours_check_for_1d() -> None:
    """Daily timeframe skips market-hours validation."""
    candles = [
        _candle(datetime(2026, 4, 19, 0, 0, tzinfo=IST), timeframe="1d"),
        _candle(datetime(2026, 4, 20, 0, 0, tzinfo=IST), timeframe="1d"),
    ]

    validate_candle_sequence(candles, timeframe="1d", symbol="NSE_EQ|INE002A01018")


def test_validate_raises_data_gap_error_for_5m() -> None:
    """5m sequence gaps greater than five minutes are rejected."""
    candles = [
        _candle(datetime(2026, 4, 19, 9, 20, tzinfo=IST)),
        _candle(datetime(2026, 4, 19, 9, 30, tzinfo=IST)),
    ]

    with pytest.raises(DataGapError, match="Data gap detected"):
        validate_candle_sequence(candles, timeframe="5m", symbol="NSE_EQ|INE002A01018")


def test_validate_passes_for_clean_sequence() -> None:
    """Valid, gap-free intraday sequence passes validation."""
    candles = [
        _candle(datetime(2026, 4, 19, 9, 20, tzinfo=IST)),
        _candle(datetime(2026, 4, 19, 9, 25, tzinfo=IST)),
        _candle(datetime(2026, 4, 19, 9, 30, tzinfo=IST)),
    ]

    validate_candle_sequence(candles, timeframe="5m", symbol="NSE_EQ|INE002A01018")


def test_validate_raises_on_timeframe_mismatch() -> None:
    """Validator rejects candles with unexpected timeframe values."""
    candles = [
        _candle(datetime(2026, 4, 19, 9, 20, tzinfo=IST), timeframe="1d"),
        _candle(datetime(2026, 4, 20, 9, 20, tzinfo=IST), timeframe="1d"),
    ]

    with pytest.raises(InvalidCandleError, match="timeframe mismatch"):
        validate_candle_sequence(candles, timeframe="5m", symbol="NSE_EQ|INE002A01018")


def test_validate_skips_intraday_gap_check_across_sessions() -> None:
    """Overnight session transition is not treated as an intraday data gap."""
    candles = [
        _candle(datetime(2026, 4, 19, 15, 30, tzinfo=IST)),
        _candle(datetime(2026, 4, 20, 9, 15, tzinfo=IST)),
    ]

    validate_candle_sequence(candles, timeframe="5m", symbol="NSE_EQ|INE002A01018")
