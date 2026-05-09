"""Integration tests for Upstox data ingestion flow."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from src.data.upstox_client import UpstoxClient
from src.db.repository import CandleRepository
from src.db.schema import create_all_tables
from src.upstox.ingester import ingest_symbol

IST = ZoneInfo("Asia/Kolkata")


class TestIngestFlow:
    """Integration tests for full ingestion pipeline."""

    def test_ingest_flow_end_to_end(self, tmp_path: Path) -> None:
        """Test complete ingestion flow from API to database."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        create_all_tables(conn)

        mock_client = MagicMock(spec=UpstoxClient)
        mock_client.fetch_historical_candles.side_effect = [
            # 1d candles
            [
                ["2024-01-15T15:30:00+05:30", "100.0", "105.0", "99.0", "104.0", "1000000", "0"],
                ["2024-01-16T15:30:00+05:30", "104.0", "106.0", "103.0", "105.5", "1100000", "0"],
            ],
            # 15m candles
            [
                ["2024-01-15T09:20:00+05:30", "100.0", "101.0", "99.0", "100.5", "10000", "0"],
                ["2024-01-15T09:35:00+05:30", "100.5", "102.0", "100.0", "101.5", "12000", "0"],
            ],
            # 5m candles
            [
                ["2024-01-15T09:20:00+05:30", "100.0", "100.5", "99.8", "100.3", "2000", "0"],
                ["2024-01-15T09:25:00+05:30", "100.3", "100.8", "100.0", "100.5", "2100", "0"],
            ],
        ]

        results = ingest_symbol(
            symbol="NIFTY",
            instrument_key="NSE_INDEX|Nifty 50",
            timeframes=["1d", "15m", "5m"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            client=mock_client,
            conn=conn,
        )

        assert results == {"1d": 2, "15m": 2, "5m": 2}

        candles_1d = CandleRepository.fetch_candles(
            conn,
            "NIFTY",
            "1d",
            datetime(2024, 1, 1, tzinfo=IST),
            datetime(2024, 1, 31, tzinfo=IST),
        )
        assert len(candles_1d) == 2
        assert candles_1d[0].symbol == "NIFTY"
        assert candles_1d[0].close == 104.0

        candles_5m = CandleRepository.fetch_candles(
            conn,
            "NIFTY",
            "5m",
            datetime(2024, 1, 1, tzinfo=IST),
            datetime(2024, 1, 31, tzinfo=IST),
        )
        assert len(candles_5m) == 2
        assert candles_5m[0].volume == 2000.0

        conn.close()

    def test_ingest_flow_validates_data(self, tmp_path: Path) -> None:
        """Test that validation is applied during ingestion."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        create_all_tables(conn)

        mock_client = MagicMock(spec=UpstoxClient)

        # Return candles with a data gap that will trigger validation error
        mock_client.fetch_historical_candles.return_value = [
            ["2024-01-15T09:20:00+05:30", "100.0", "101.0", "99.0", "100.5", "1000", "0"],
            # Gap: should be 09:25 but it's 09:40 (15 minute gap in 5m timeframe)
            ["2024-01-15T09:40:00+05:30", "100.5", "102.0", "100.0", "101.5", "1200", "0"],
        ]

        from src.utils.exceptions import DataGapError

        with pytest.raises(DataGapError):
            ingest_symbol(
                symbol="NIFTY",
                instrument_key="NSE_INDEX|Nifty 50",
                timeframes=["5m"],
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 31),
                client=mock_client,
                conn=conn,
            )

        conn.close()

    def test_ingest_flow_preserves_duplicate_handling(self, tmp_path: Path) -> None:
        """Test that duplicate candles are ignored during insert."""
        db_path = tmp_path / "test.db"
        conn = sqlite3.connect(str(db_path))
        create_all_tables(conn)

        # Insert two candles first to meet minimum validation requirement
        from src.models.candle import Candle

        candle1 = Candle(
            symbol="NIFTY",
            timeframe="5m",
            timestamp=datetime(2024, 1, 15, 9, 20, tzinfo=IST),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000.0,
        )
        candle2 = Candle(
            symbol="NIFTY",
            timeframe="5m",
            timestamp=datetime(2024, 1, 15, 9, 25, tzinfo=IST),
            open=100.5,
            high=101.5,
            low=100.0,
            close=101.0,
            volume=1100.0,
        )
        CandleRepository.insert_candles(conn, [candle1, candle2])

        mock_client = MagicMock(spec=UpstoxClient)
        # Try to ingest the same candles again (duplicate)
        mock_client.fetch_historical_candles.return_value = [
            ["2024-01-15T09:20:00+05:30", "100.0", "101.0", "99.0", "100.5", "1000", "0"],
            ["2024-01-15T09:25:00+05:30", "100.5", "101.5", "100.0", "101.0", "1100", "0"],
        ]

        results = ingest_symbol(
            symbol="NIFTY",
            instrument_key="NSE_INDEX|Nifty 50",
            timeframes=["5m"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 31),
            client=mock_client,
            conn=conn,
        )

        assert results["5m"] == 2

        candles = CandleRepository.fetch_candles(
            conn,
            "NIFTY",
            "5m",
            datetime(2024, 1, 1, tzinfo=IST),
            datetime(2024, 1, 31, tzinfo=IST),
        )
        assert len(candles) == 2

        conn.close()
