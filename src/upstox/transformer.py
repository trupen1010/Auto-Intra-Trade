"""Transform raw Upstox API candle data to domain models."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from src.models.candle import Candle

IST = ZoneInfo("Asia/Kolkata")


def transform_candles(
    raw_candles: list[dict],
    symbol: str,
    timeframe: str,
) -> list[Candle]:
    """Convert raw Upstox API candles to Candle domain models.

    Upstox candle format (each item in response data.candles):
      [timestamp_str, open, high, low, close, volume, oi]

    Args:
        raw_candles: List of raw candle arrays from Upstox API.
        symbol: Instrument symbol.
        timeframe: Timeframe string (e.g. "5m", "15m", "1d").

    Returns:
        List of Candle domain models, sorted ascending by timestamp.
    """
    candles: list[Candle] = []

    for row in raw_candles:
        timestamp_str = row[0]
        open_price = float(row[1])
        high_price = float(row[2])
        low_price = float(row[3])
        close_price = float(row[4])
        volume = float(row[5])

        timestamp = datetime.fromisoformat(timestamp_str).astimezone(IST)

        candle = Candle(
            symbol=symbol,
            timeframe=timeframe,
            timestamp=timestamp,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
        )
        candles.append(candle)

    candles.sort(key=lambda c: c.timestamp)
    return candles
