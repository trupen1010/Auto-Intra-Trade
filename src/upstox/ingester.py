"""Orchestrate candle ingestion from Upstox API to SQLite."""

from __future__ import annotations

import logging
import sqlite3
from datetime import date
from time import sleep

from src.data.upstox_client import UpstoxClient
from src.data.validator import validate_candle_sequence
from src.db.repository import CandleRepository
from src.utils.enums import Timeframe
from src.upstox.transformer import transform_candles

logger = logging.getLogger(__name__)

_TIMEFRAME_TO_INTERVAL = {
    Timeframe.ONE_DAY: "1d",
    Timeframe.FIFTEEN_MINUTE: "15m",
    Timeframe.FIVE_MINUTE: "5m",
}

_REQUEST_DELAY_SECONDS = 0.25  # Rate limit: ~250 req/min


def ingest_symbol(
    symbol: str,
    instrument_key: str,
    timeframes: list[str],
    start_date: date,
    end_date: date,
    client: UpstoxClient,
    conn: sqlite3.Connection,
) -> dict[str, int]:
    """Ingest candles for a symbol across multiple timeframes.

    For each timeframe:
      1. Fetch historical candles from Upstox API
      2. Transform to Candle domain models
      3. Validate sequence integrity
      4. Upsert into SQLite database
      5. Log count of candles ingested

    Args:
        symbol: Trading symbol (e.g. "NIFTY").
        instrument_key: Upstox instrument key (e.g. "NSE_INDEX|Nifty 50").
        timeframes: List of timeframe strings (e.g. ["1d", "15m", "5m"]).
        start_date: Inclusive start date for candle fetch.
        end_date: Inclusive end date for candle fetch.
        client: UpstoxClient instance for API calls.
        conn: Open SQLite connection (caller manages lifecycle).

    Returns:
        Dictionary mapping timeframe -> candles_ingested count.

    Raises:
        ValueError: If timeframe is unsupported or validation fails.
        Exception: Propagates errors from API, transformation, or validation.
    """
    results: dict[str, int] = {}

    for timeframe in timeframes:
        logger.info(f"Fetching {timeframe} candles for {symbol}...")

        raw_candles = client.fetch_historical_candles(
            symbol=instrument_key,
            timeframe=timeframe,
            from_date=start_date,
            to_date=end_date,
        )
        logger.info(f"  Received {len(raw_candles)} raw candles")

        candles = transform_candles(raw_candles, symbol, timeframe)
        logger.info(f"  Transformed to {len(candles)} Candle domain models")

        validate_candle_sequence(candles, timeframe, symbol)
        logger.info(f"  Validated sequence integrity")

        CandleRepository.insert_candles(conn, candles)
        logger.info(f"  Inserted {len(candles)} candles into database")

        results[timeframe] = len(candles)

        sleep(_REQUEST_DELAY_SECONDS)

    return results
