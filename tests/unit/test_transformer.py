"""Unit tests for raw candle transformation."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.data.transformer import transform_candles
from src.utils.exceptions import InvalidCandleError

IST = ZoneInfo("Asia/Kolkata")


def test_transform_valid_upstox_rows_returns_candle_list() -> None:
    """Valid Upstox list rows are transformed into Candle models."""
    raw_rows = [
        ["2026-04-19T09:20:00+05:30", 100.0, 101.0, 99.0, 100.5, 1000.0, 0.0],
        ["2026-04-19T09:25:00+05:30", 100.5, 102.0, 100.0, 101.5, 1200.0, 0.0],
    ]

    candles = transform_candles(raw_rows, symbol="NSE_EQ|INE002A01018", timeframe="5m")

    assert len(candles) == 2
    assert candles[0].timestamp == datetime(2026, 4, 19, 9, 20, tzinfo=IST)
    assert candles[0].open == 100.0
    assert candles[1].close == 101.5
    assert candles[1].volume == 1200.0


def test_transform_raises_on_wrong_row_length() -> None:
    """Rows that do not have seven fields are rejected."""
    raw_rows = [["2026-04-19T09:20:00+05:30", 100.0, 101.0, 99.0, 100.5, 1000.0]]

    with pytest.raises(InvalidCandleError, match="expected 7 fields"):
        transform_candles(raw_rows, symbol="NSE_EQ|INE002A01018", timeframe="5m")


def test_transform_raises_on_negative_ohlcv() -> None:
    """Negative OHLCV values raise InvalidCandleError."""
    raw_rows = [["2026-04-19T09:20:00+05:30", -100.0, 101.0, 99.0, 100.5, 1000.0, 0.0]]

    with pytest.raises(InvalidCandleError, match="positive numbers"):
        transform_candles(raw_rows, symbol="NSE_EQ|INE002A01018", timeframe="5m")


def test_transform_allows_zero_volume() -> None:
    """Rows with zero volume remain valid."""
    raw_rows = [["2026-04-19T09:20:00+05:30", 100.0, 101.0, 99.0, 100.5, 0.0, 0.0]]

    candles = transform_candles(raw_rows, symbol="NSE_EQ|INE002A01018", timeframe="5m")

    assert candles[0].volume == 0.0


def test_transform_result_is_sorted_ascending() -> None:
    """Returned candle list is sorted ascending by timestamp."""
    raw_rows = [
        ["2026-04-19T09:25:00+05:30", 100.5, 102.0, 100.0, 101.5, 1200.0, 0.0],
        ["2026-04-19T09:20:00+05:30", 100.0, 101.0, 99.0, 100.5, 1000.0, 0.0],
    ]

    candles = transform_candles(raw_rows, symbol="NSE_EQ|INE002A01018", timeframe="5m")

    assert candles[0].timestamp < candles[1].timestamp


def test_transform_raises_on_unparseable_timestamp() -> None:
    """Invalid ISO8601 timestamps are rejected."""
    raw_rows = [["2026-13-19 09:20:00", 100.0, 101.0, 99.0, 100.5, 1000.0, 0.0]]

    with pytest.raises(InvalidCandleError, match="Invalid candle timestamp"):
        transform_candles(raw_rows, symbol="NSE_EQ|INE002A01018", timeframe="5m")


def test_transform_raises_on_invalid_ohlc_bounds() -> None:
    """Rows with logically invalid OHLC bounds are rejected."""
    raw_rows = [["2026-04-19T09:20:00+05:30", 101.0, 100.0, 99.0, 100.5, 1000.0, 0.0]]

    with pytest.raises(InvalidCandleError, match="OHLC bounds"):
        transform_candles(raw_rows, symbol="NSE_EQ|INE002A01018", timeframe="5m")
