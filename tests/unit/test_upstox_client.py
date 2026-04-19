"""Unit tests for Upstox historical candle client."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest
import requests

from src.data.upstox_client import UpstoxClient
from src.utils.exceptions import BacktestEngineError, InsufficientDataError


def test_fetch_returns_candle_list_on_success() -> None:
    """Successful fetch returns raw candle rows from response payload."""
    client = UpstoxClient(access_token="token")
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "data": {
            "candles": [
                {"open": 100.0, "high": 101.0, "low": 99.5, "close": 100.5},
                {"open": 100.5, "high": 101.5, "low": 100.0, "close": 101.0},
            ]
        }
    }

    with patch("src.data.upstox_client.requests.get", return_value=mock_response) as mock_get:
        candles = client.fetch_historical_candles(
            symbol="NSE_EQ|INE002A01018",
            timeframe="5m",
            from_date=date(2026, 4, 1),
            to_date=date(2026, 4, 2),
        )

    assert len(candles) == 2
    mock_get.assert_called_once_with(
        "https://api.upstox.com/v2/historical-candle/NSE_EQ|INE002A01018/5minute/2026-04-02/2026-04-01",
        headers={"Authorisation": "Bearer token"},
        timeout=30,
    )


def test_fetch_raises_insufficient_data_on_empty_candles() -> None:
    """Empty candles list raises InsufficientDataError."""
    client = UpstoxClient(access_token="token")
    mock_response = MagicMock()
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {"data": {"candles": []}}

    with patch("src.data.upstox_client.requests.get", return_value=mock_response):
        with pytest.raises(InsufficientDataError):
            client.fetch_historical_candles(
                symbol="NSE_EQ|INE002A01018",
                timeframe="15m",
                from_date=date(2026, 4, 1),
                to_date=date(2026, 4, 2),
            )


def test_fetch_raises_on_http_error() -> None:
    """HTTP errors are wrapped as BacktestEngineError."""
    client = UpstoxClient(access_token="token")
    mock_response = MagicMock()
    mock_response.raise_for_status.side_effect = requests.HTTPError("boom")

    with patch("src.data.upstox_client.requests.get", return_value=mock_response):
        with pytest.raises(BacktestEngineError):
            client.fetch_historical_candles(
                symbol="NSE_EQ|INE002A01018",
                timeframe="1d",
                from_date=date(2026, 4, 1),
                to_date=date(2026, 4, 2),
            )


def test_fetch_raises_on_connection_error() -> None:
    """Connection errors are wrapped as BacktestEngineError."""
    client = UpstoxClient(access_token="token")

    with patch(
        "src.data.upstox_client.requests.get",
        side_effect=requests.ConnectionError("offline"),
    ):
        with pytest.raises(BacktestEngineError):
            client.fetch_historical_candles(
                symbol="NSE_EQ|INE002A01018",
                timeframe="1d",
                from_date=date(2026, 4, 1),
                to_date=date(2026, 4, 2),
            )


def test_timeframe_mapping() -> None:
    """Timeframe map matches required Upstox intervals."""
    assert UpstoxClient.TIMEFRAME_TO_INTERVAL["5m"] == "5minute"
    assert UpstoxClient.TIMEFRAME_TO_INTERVAL["15m"] == "15minute"
    assert UpstoxClient.TIMEFRAME_TO_INTERVAL["1d"] == "day"
