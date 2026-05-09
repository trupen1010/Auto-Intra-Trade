"""Unit tests for Upstox candle ingestion orchestration."""

from __future__ import annotations

import sqlite3
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from src.models.candle import Candle
from src.upstox.ingester import ingest_symbol

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
