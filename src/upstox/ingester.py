"""Orchestrate candle ingestion from Upstox API to SQLite."""

from __future__ import annotations

import logging
import sqlite3
from datetime import date, timedelta
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

# Upstox V3 API constraints: max data per request
_API_LIMITS = {
    "1d": {"days": 3650},  # ~10 years
    "15m": {"days": 30},  # 1 month
    "5m": {"days": 30},  # 1 month
}

# Data availability in Upstox V3
_DATA_AVAILABILITY = {
    "1d": date(2000, 1, 1),
    "15m": date(2022, 1, 1),
    "5m": date(2022, 1, 1),
}


def _generate_date_chunks(
    timeframe: str, start_date: date, end_date: date
) -> list[tuple[date, date]]:
    """Generate (from_date, to_date) chunks respecting API limits.

    Args:
        timeframe: "1d", "15m", or "5m".
        start_date: Inclusive start date.
        end_date: Inclusive end date.

    Returns:
        List of (from_date, to_date) tuples, sorted chronologically ascending.
    """
    if timeframe not in _API_LIMITS:
        raise ValueError(f"Unsupported timeframe: {timeframe}")

    max_days = _API_LIMITS[timeframe]["days"]
    chunks = []

    # Build chunks from end_date backwards to start_date
    current_to = end_date
    while current_to >= start_date:
        current_from = current_to - timedelta(days=max_days)
        if current_from < start_date:
            current_from = start_date
        chunks.append((current_from, current_to))
        current_to = current_from - timedelta(days=1)

    # Reverse to chronological order (oldest to newest)
    chunks.reverse()
    return chunks


def ingest_symbol(
    symbol: str,
    instrument_key: str,
    timeframes: list[str],
    start_date: date,
    end_date: date,
    client: UpstoxClient,
    conn: sqlite3.Connection,
    fetch_all_available: bool = False,
) -> dict[str, int]:
    """Ingest candles for a symbol across multiple timeframes.

    For each timeframe:
      1. Fetch historical candles (in chunks if needed) from Upstox API
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
        fetch_all_available: If True, fetch all available data from earliest date.
            If False, fetch only data between start_date and end_date.

    Returns:
        Dictionary mapping timeframe -> candles_ingested count.
        Skipped timeframes due to API errors are excluded from results.

    Raises:
        ValueError: If timeframe is unsupported or validation fails.
        Exception: Propagates non-API errors from transformation or validation.
    """
    results: dict[str, int] = {}

    for timeframe in timeframes:
        logger.info(f"Fetching {timeframe} candles for {symbol}...")

        # Determine fetch range
        if fetch_all_available:
            fetch_start = _DATA_AVAILABILITY.get(timeframe, start_date)
            fetch_end = end_date
        else:
            fetch_start = start_date
            fetch_end = end_date

        # Generate date chunks respecting API limits
        chunks = _generate_date_chunks(timeframe, fetch_start, fetch_end)
        logger.info(f"  Will fetch in {len(chunks)} chunk(s)")

        all_raw_candles = []

        # Fetch each chunk
        for chunk_idx, (chunk_from, chunk_to) in enumerate(chunks, 1):
            logger.info(f"  Chunk {chunk_idx}/{len(chunks)}: {chunk_from} to {chunk_to}")

            try:
                raw_candles = client.fetch_historical_candles(
                    symbol=instrument_key,
                    timeframe=timeframe,
                    from_date=chunk_from,
                    to_date=chunk_to,
                )
                all_raw_candles.extend(raw_candles)
                logger.info(f"    Received {len(raw_candles)} raw candles")
            except Exception as e:
                logger.warning(
                    f"    Chunk {chunk_idx} skipped: API unavailable ({type(e).__name__})"
                )
                sleep(_REQUEST_DELAY_SECONDS)
                continue

            sleep(_REQUEST_DELAY_SECONDS)

        if not all_raw_candles:
            logger.warning(f"  Skipped {timeframe}: No candles fetched")
            continue

        logger.info(f"  Total: {len(all_raw_candles)} raw candles across all chunks")

        candles = transform_candles(all_raw_candles, symbol, timeframe)
        logger.info(f"  Transformed to {len(candles)} Candle domain models")

        validate_candle_sequence(candles, timeframe, symbol)
        logger.info(f"  Validated sequence integrity")

        CandleRepository.insert_candles(conn, candles)
        logger.info(f"  Inserted {len(candles)} candles into database")

        results[timeframe] = len(candles)

    return results
