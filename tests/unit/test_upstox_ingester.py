"""Unit tests for Upstox candle ingestion orchestration."""

from __future__ import annotations

import sqlite3
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.models.candle import Candle
from src.upstox.ingester import _generate_date_chunks, ingest_symbol

IST_TZ = "Asia/Kolkata"


class TestIngestSymbol:
    """Tests for candle ingestion from Upstox API to SQLite."""

    def test_ingest_symbol_returns_correct_counts(self, tmp_path) -> None:
        """Test that ingest_symbol returns count per timeframe."""
        conn = sqlite3.connect(":memory:")

        from src.db.schema import create_all_tables

        create_all_tables(conn)

        mock_client = MagicMock()
        mock_client.fetch_historical_candles.return_value = [
            ["2024-01-15T09:20:00+05:30", "100.0", "101.0", "99.0", "100.5", "1000", "0"],
        ]

        with patch("src.upstox.ingester.validate_candle_sequence"):
            with patch("src.upstox.ingester.CandleRepository.insert_candles"):
                results = ingest_symbol(
                    symbol="NIFTY",
                    instrument_key="NSE_INDEX|Nifty 50",
                    timeframes=["1d", "15m", "5m"],
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                    client=mock_client,
                    conn=conn,
                )

        assert len(results) == 3
        assert results["1d"] == 1
        assert results["15m"] == 1
        assert results["5m"] == 1

    def test_ingest_symbol_calls_validator(self) -> None:
        """Test that ingest_symbol validates each candle sequence."""
        conn = MagicMock()

        mock_client = MagicMock()
        mock_client.fetch_historical_candles.return_value = [
            ["2024-01-15T09:20:00+05:30", "100.0", "101.0", "99.0", "100.5", "1000", "0"],
        ]

        with patch("src.upstox.ingester.validate_candle_sequence") as mock_validator:
            with patch("src.upstox.ingester.CandleRepository.insert_candles"):
                ingest_symbol(
                    symbol="NIFTY",
                    instrument_key="NSE_INDEX|Nifty 50",
                    timeframes=["1d", "15m", "5m"],
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                    client=mock_client,
                    conn=conn,
                )

        assert mock_validator.call_count == 3

    def test_ingest_symbol_calls_client_for_each_timeframe(self) -> None:
        """Test that ingest_symbol fetches each timeframe separately."""
        conn = MagicMock()

        mock_client = MagicMock()
        mock_client.fetch_historical_candles.return_value = [
            ["2024-01-15T09:20:00+05:30", "100.0", "101.0", "99.0", "100.5", "1000", "0"],
        ]

        with patch("src.upstox.ingester.validate_candle_sequence"):
            with patch("src.upstox.ingester.CandleRepository.insert_candles"):
                ingest_symbol(
                    symbol="NIFTY",
                    instrument_key="NSE_INDEX|Nifty 50",
                    timeframes=["1d", "15m", "5m"],
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                    client=mock_client,
                    conn=conn,
                )

        assert mock_client.fetch_historical_candles.call_count == 3

    def test_ingest_symbol_calls_repository_insert(self) -> None:
        """Test that ingest_symbol inserts candles into database."""
        conn = MagicMock()

        mock_client = MagicMock()
        mock_client.fetch_historical_candles.return_value = [
            ["2024-01-15T09:20:00+05:30", "100.0", "101.0", "99.0", "100.5", "1000", "0"],
        ]

        with patch("src.upstox.ingester.validate_candle_sequence"):
            with patch("src.upstox.ingester.CandleRepository.insert_candles") as mock_insert:
                ingest_symbol(
                    symbol="NIFTY",
                    instrument_key="NSE_INDEX|Nifty 50",
                    timeframes=["1d", "15m", "5m"],
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                    client=mock_client,
                    conn=conn,
                )

        assert mock_insert.call_count == 3

    def test_ingest_symbol_propagates_validation_error(self) -> None:
        """Test that validation errors are propagated."""
        conn = MagicMock()

        mock_client = MagicMock()
        mock_client.fetch_historical_candles.return_value = [
            ["2024-01-15T09:20:00+05:30", "100.0", "101.0", "99.0", "100.5", "1000", "0"],
        ]

        with patch(
            "src.upstox.ingester.validate_candle_sequence",
            side_effect=ValueError("Invalid sequence"),
        ):
            with pytest.raises(ValueError, match="Invalid sequence"):
                ingest_symbol(
                    symbol="NIFTY",
                    instrument_key="NSE_INDEX|Nifty 50",
                    timeframes=["1d"],
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                    client=mock_client,
                    conn=conn,
                )

    def test_ingest_symbol_skips_unavailable_timeframes(self) -> None:
        """Test that unavailable timeframes are skipped gracefully."""
        conn = MagicMock()

        mock_client = MagicMock()
        mock_client.fetch_historical_candles.side_effect = ValueError("API error")

        with patch("src.upstox.ingester.validate_candle_sequence"):
            with patch("src.upstox.ingester.CandleRepository.insert_candles"):
                results = ingest_symbol(
                    symbol="NIFTY",
                    instrument_key="NSE_INDEX|Nifty 50",
                    timeframes=["1d"],
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                    client=mock_client,
                    conn=conn,
                )

        assert results == {}

    def test_ingest_symbol_fetches_multiple_chunks(self) -> None:
        """Test that ingest_symbol fetches in chunks for 15m data."""
        conn = MagicMock()

        mock_client = MagicMock()
        mock_client.fetch_historical_candles.return_value = [
            ["2024-01-15T09:20:00+05:30", "100.0", "101.0", "99.0", "100.5", "1000", "0"],
        ]

        with patch("src.upstox.ingester.validate_candle_sequence"):
            with patch("src.upstox.ingester.CandleRepository.insert_candles"):
                # 60-day range requires 2 chunks for 15m (30-day limit)
                ingest_symbol(
                    symbol="NIFTY",
                    instrument_key="NSE_INDEX|Nifty 50",
                    timeframes=["15m"],
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 2, 29),
                    client=mock_client,
                    conn=conn,
                )

        # Should call API twice (2 chunks)
        assert mock_client.fetch_historical_candles.call_count == 2

    def test_ingest_symbol_with_fetch_all_available(self) -> None:
        """Test that fetch_all_available extends date range."""
        conn = MagicMock()

        mock_client = MagicMock()
        mock_client.fetch_historical_candles.return_value = [
            ["2024-01-15T09:20:00+05:30", "100.0", "101.0", "99.0", "100.5", "1000", "0"],
        ]

        with patch("src.upstox.ingester.validate_candle_sequence"):
            with patch("src.upstox.ingester.CandleRepository.insert_candles"):
                ingest_symbol(
                    symbol="NIFTY",
                    instrument_key="NSE_INDEX|Nifty 50",
                    timeframes=["1d"],
                    start_date=date(2024, 1, 1),
                    end_date=date(2024, 1, 31),
                    client=mock_client,
                    conn=conn,
                    fetch_all_available=True,
                )

        # Should fetch from 2000-01-01 (earliest date for 1d data)
        calls = mock_client.fetch_historical_candles.call_args_list
        assert calls[0][1]["from_date"] == date(2000, 1, 1)


class TestGenerateDateChunks:
    """Tests for date chunk generation."""

    def test_single_chunk_within_limit(self) -> None:
        """Test that small date range fits in single chunk."""
        chunks = _generate_date_chunks("1d", date(2024, 1, 1), date(2024, 1, 31))
        assert len(chunks) == 1
        assert chunks[0] == (date(2024, 1, 1), date(2024, 1, 31))

    def test_multiple_chunks_for_15m(self) -> None:
        """Test that 60-day range generates 2 chunks for 15m."""
        chunks = _generate_date_chunks("15m", date(2024, 1, 1), date(2024, 2, 29))
        assert len(chunks) == 2
        # Chunks should be in chronological order
        assert chunks[0][0] < chunks[1][0]

    def test_chunks_respect_api_limits(self) -> None:
        """Test that chunks respect API day limits."""
        # 1d has 3650-day limit (~10 years)
        chunks = _generate_date_chunks("1d", date(2000, 1, 1), date(2030, 1, 1))
        for chunk_from, chunk_to in chunks:
            days = (chunk_to - chunk_from).days
            assert days <= 3650  # Within limit

    def test_chunks_chronological_order(self) -> None:
        """Test that chunks are in chronological ascending order."""
        chunks = _generate_date_chunks("5m", date(2022, 1, 1), date(2024, 12, 31))
        for i in range(len(chunks) - 1):
            assert chunks[i][1] < chunks[i + 1][0]  # No overlap

    def test_invalid_timeframe_raises_error(self) -> None:
        """Test that invalid timeframe raises ValueError."""
        with pytest.raises(ValueError, match="Unsupported timeframe"):
            _generate_date_chunks("30m", date(2024, 1, 1), date(2024, 1, 31))
