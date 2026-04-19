"""Upstox API adapter for historical candle retrieval."""

from __future__ import annotations

from datetime import date

import requests

from src.utils.exceptions import BacktestEngineError, InsufficientDataError


class UpstoxClient:
    """HTTP adapter for Upstox historical candle endpoints.

    For NSE equities, pass instrument keys in the format ``NSE_EQ|{ISIN}`` as the
    ``symbol`` argument. This client forwards the key as-is and does not validate it.
    """

    BASE_URL = "https://api.upstox.com/v2"
    TIMEFRAME_TO_INTERVAL: dict[str, str] = {
        "5m": "5minute",
        "15m": "15minute",
        "1d": "day",
    }
    REQUEST_TIMEOUT_SECONDS = 30

    def __init__(self, access_token: str) -> None:
        """Initialize the Upstox client.

        Args:
            access_token: Upstox API access token used as a Bearer token.
        """
        self._access_token = access_token

    def fetch_historical_candles(
        self,
        symbol: str,
        timeframe: str,
        from_date: date,
        to_date: date,
    ) -> list[dict]:
        """Fetch historical candle rows from Upstox v2 API.

        Args:
            symbol: Upstox instrument key (e.g. ``NSE_EQ|{ISIN}``).
            timeframe: Candle timeframe string: ``5m``, ``15m``, or ``1d``.
            from_date: Inclusive start date for data fetch.
            to_date: Inclusive end date for data fetch.

        Returns:
            Raw candle dictionaries from ``response["data"]["candles"]``.

        Raises:
            ValueError: If timeframe is unsupported.
            InsufficientDataError: If API returns no candle rows.
            BacktestEngineError: If request fails with HTTP or connection error.
        """
        interval = self.TIMEFRAME_TO_INTERVAL.get(timeframe)
        if interval is None:
            raise ValueError(f"Unsupported timeframe: {timeframe}")

        endpoint = (
            f"{self.BASE_URL}/historical-candle/"
            f"{symbol}/{interval}/{to_date.isoformat()}/{from_date.isoformat()}"
        )
        headers = {"Authorisation": f"Bearer {self._access_token}"}

        try:
            response = requests.get(
                endpoint,
                headers=headers,
                timeout=self.REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
        except (requests.HTTPError, requests.ConnectionError) as exc:
            msg = f"Failed to fetch candles for symbol '{symbol}' on timeframe '{timeframe}'."
            raise BacktestEngineError(msg) from exc

        payload = response.json()
        candles: list[dict] = payload["data"]["candles"]
        if not candles:
            msg = (
                f"No candle data returned for symbol '{symbol}', timeframe '{timeframe}', "
                f"from {from_date.isoformat()} to {to_date.isoformat()}."
            )
            raise InsufficientDataError(msg)
        return candles
