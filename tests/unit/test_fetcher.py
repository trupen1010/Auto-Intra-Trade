"""Unit tests for data fetch orchestration."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from src.data.fetcher import fetch_and_store_candles
from src.models.candle import Candle
from src.utils.exceptions import InsufficientDataError, InvalidCandleError

IST = ZoneInfo("Asia/Kolkata")


def _candle(ts: datetime) -> Candle:
    """Create a candle fixture for fetcher tests."""
    return Candle(
        symbol="NSE_EQ|INE002A01018",
        timeframe="5m",
        timestamp=ts,
        open=100.0,
        high=101.0,
        low=99.0,
        close=100.5,
        volume=1000.0,
    )


def test_fetch_and_store_calls_all_stages_in_order() -> None:
    """Fetcher invokes client, transform, validate, and repository in strict order."""
    client = MagicMock()
    raw = [["2026-04-19T09:20:00+05:30", 100.0, 101.0, 99.0, 100.5, 1000.0, 0.0]]
    candles = [_candle(datetime(2026, 4, 19, 9, 20, tzinfo=IST))]
    call_order: list[str] = []

    client.fetch_historical_candles.side_effect = lambda *args: call_order.append("fetch") or raw

    with sqlite3.connect(":memory:") as conn:
        with (
            patch(
                "src.data.fetcher.transform_candles",
                side_effect=lambda *args: call_order.append("transform") or candles,
            ) as mock_transform,
            patch(
                "src.data.fetcher.validate_candle_sequence",
                side_effect=lambda *args: call_order.append("validate"),
            ) as mock_validate,
            patch(
                "src.data.fetcher.CandleRepository.insert_candles",
                side_effect=lambda *args: call_order.append("insert"),
            ) as mock_insert,
        ):
            result = fetch_and_store_candles(
                client=client,
                conn=conn,
                symbol="NSE_EQ|INE002A01018",
                timeframe="5m",
                from_date=date(2026, 4, 1),
                to_date=date(2026, 4, 2),
            )

        assert result == candles
        assert call_order == ["fetch", "transform", "validate", "insert"]
        client.fetch_historical_candles.assert_called_once_with(
            "NSE_EQ|INE002A01018",
            "5m",
            date(2026, 4, 1),
            date(2026, 4, 2),
        )
        mock_transform.assert_called_once_with(raw, "NSE_EQ|INE002A01018", "5m")
        mock_validate.assert_called_once_with(candles, "5m", "NSE_EQ|INE002A01018")
        mock_insert.assert_called_once_with(conn, candles)


def test_fetch_and_store_returns_candle_list() -> None:
    """Fetcher returns the transformed and validated candle list."""
    client = MagicMock()
    raw = [["2026-04-19T09:20:00+05:30", 100.0, 101.0, 99.0, 100.5, 1000.0, 0.0]]
    candles = [_candle(datetime(2026, 4, 19, 9, 20, tzinfo=IST))]
    client.fetch_historical_candles.return_value = raw

    with sqlite3.connect(":memory:") as conn:
        with (
            patch("src.data.fetcher.transform_candles", return_value=candles),
            patch("src.data.fetcher.validate_candle_sequence"),
            patch("src.data.fetcher.CandleRepository.insert_candles"),
        ):
            result = fetch_and_store_candles(
                client=client,
                conn=conn,
                symbol="NSE_EQ|INE002A01018",
                timeframe="5m",
                from_date=date(2026, 4, 1),
                to_date=date(2026, 4, 2),
            )

    assert result == candles


def test_fetch_and_store_propagates_insufficient_data_error() -> None:
    """Fetcher propagates InsufficientDataError without wrapping."""
    client = MagicMock()
    error = InsufficientDataError("not enough candles")
    client.fetch_historical_candles.side_effect = error

    with sqlite3.connect(":memory:") as conn:
        with pytest.raises(InsufficientDataError) as exc_info:
            fetch_and_store_candles(
                client=client,
                conn=conn,
                symbol="NSE_EQ|INE002A01018",
                timeframe="5m",
                from_date=date(2026, 4, 1),
                to_date=date(2026, 4, 2),
            )

    assert exc_info.value is error


def test_fetch_and_store_propagates_invalid_candle_error() -> None:
    """Fetcher propagates InvalidCandleError from validation without wrapping."""
    client = MagicMock()
    raw = [["2026-04-19T09:20:00+05:30", 100.0, 101.0, 99.0, 100.5, 1000.0, 0.0]]
    candles = [_candle(datetime(2026, 4, 19, 9, 20, tzinfo=IST))]
    error = InvalidCandleError("bad candle")
    client.fetch_historical_candles.return_value = raw

    with sqlite3.connect(":memory:") as conn:
        with (
            patch("src.data.fetcher.transform_candles", return_value=candles),
            patch("src.data.fetcher.validate_candle_sequence", side_effect=error),
            patch("src.data.fetcher.CandleRepository.insert_candles") as mock_insert,
        ):
            with pytest.raises(InvalidCandleError) as exc_info:
                fetch_and_store_candles(
                    client=client,
                    conn=conn,
                    symbol="NSE_EQ|INE002A01018",
                    timeframe="5m",
                    from_date=date(2026, 4, 1),
                    to_date=date(2026, 4, 2),
                )

    assert exc_info.value is error
    mock_insert.assert_not_called()
