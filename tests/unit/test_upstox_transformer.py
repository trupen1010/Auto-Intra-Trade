"""Unit tests for Upstox candle transformation.

This file tests the canonical transform_candles implementation in
src.data.transformer (the weaker src.upstox.transformer has been removed).
"""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.data.transformer import transform_candles

IST = ZoneInfo("Asia/Kolkata")


class TestTransformCandles:
    """Tests for raw Upstox candle transformation to domain models."""

    def test_transform_candles_parses_timestamp_as_ist(self) -> None:
        """Test that timestamps are parsed and converted to IST."""
        raw_candles = [
            ["2024-01-15T09:20:00+05:30", "100.0", "101.0", "99.0", "100.5", "1000", "0"],
        ]

        result = transform_candles(raw_candles, "NIFTY", "5m")

        assert len(result) == 1
        candle = result[0]
        assert candle.timestamp.tzinfo == IST
        assert candle.timestamp.year == 2024
        assert candle.timestamp.month == 1
        assert candle.timestamp.day == 15

    def test_transform_candles_sorted_ascending(self) -> None:
        """Test that transformed candles are sorted by timestamp ascending."""
        raw_candles = [
            ["2024-01-15T09:30:00+05:30", "100.0", "101.0", "99.0", "100.5", "1000", "0"],
            ["2024-01-15T09:20:00+05:30", "99.0", "100.0", "98.0", "99.5", "1100", "0"],
            ["2024-01-15T09:25:00+05:30", "99.5", "100.5", "99.0", "100.0", "1050", "0"],
        ]

        result = transform_candles(raw_candles, "NIFTY", "5m")

        assert len(result) == 3
        timestamps = [c.timestamp for c in result]
        assert timestamps == sorted(timestamps)

    def test_transform_candles_discards_oi_field(self) -> None:
        """Test that Open Interest (OI) field is discarded."""
        raw_candles = [
            ["2024-01-15T09:20:00+05:30", "100.0", "101.0", "99.0", "100.5", "1000", "9999"],
        ]

        result = transform_candles(raw_candles, "NIFTY", "5m")

        assert len(result) == 1
        candle = result[0]
        assert not hasattr(candle, "oi")

    def test_transform_candles_preserves_ohlcv_values(self) -> None:
        """Test that OHLCV values are correctly preserved."""
        raw_candles = [
            ["2024-01-15T09:20:00+05:30", "100.0", "101.5", "99.5", "100.5", "2500", "0"],
        ]

        result = transform_candles(raw_candles, "NIFTY", "5m")

        candle = result[0]
        assert candle.open == 100.0
        assert candle.high == 101.5
        assert candle.low == 99.5
        assert candle.close == 100.5
        assert candle.volume == 2500.0

    def test_transform_empty_returns_empty_list(self) -> None:
        """Test that empty input returns empty list."""
        result = transform_candles([], "NIFTY", "5m")
        assert result == []

    def test_transform_candles_sets_symbol_and_timeframe(self) -> None:
        """Test that symbol and timeframe are set correctly."""
        raw_candles = [
            ["2024-01-15T09:20:00+05:30", "100.0", "101.0", "99.0", "100.5", "1000", "0"],
        ]

        result = transform_candles(raw_candles, "SBIN", "15m")

        candle = result[0]
        assert candle.symbol == "SBIN"
        assert candle.timeframe == "15m"
