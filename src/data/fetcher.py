"""Data fetch orchestration for client, transform, validate, and persistence stages."""

from __future__ import annotations

import sqlite3
from datetime import date

from src.data.transformer import transform_candles
from src.data.upstox_client import UpstoxClient
from src.data.validator import validate_candle_sequence
from src.db.repository import CandleRepository
from src.models.candle import Candle


def fetch_and_store_candles(
    client: UpstoxClient,
    conn: sqlite3.Connection,
    symbol: str,
    timeframe: str,
    from_date: date,
    to_date: date,
) -> list[Candle]:
    """Fetch, transform, validate, and store candles for one symbol/timeframe/date range.

    Args:
        client: Upstox API client adapter.
        conn: Open SQLite connection for persistence.
        symbol: Instrument symbol to fetch.
        timeframe: Candle timeframe to fetch.
        from_date: Inclusive fetch start date.
        to_date: Inclusive fetch end date.

    Returns:
        The validated list of Candle objects that was persisted to storage.
    """
    raw = client.fetch_historical_candles(symbol, timeframe, from_date, to_date)
    candles = transform_candles(raw, symbol, timeframe)
    validate_candle_sequence(candles, timeframe, symbol)
    CandleRepository.insert_candles(conn, candles)
    return candles
