"""Raw candle transformation utilities."""

from __future__ import annotations

from datetime import datetime
from numbers import Real

from src.models.candle import Candle
from src.utils.datetime_utils import to_ist
from src.utils.exceptions import InvalidCandleError

_UPSTOX_CANDLE_ROW_LENGTH = 7


def transform_candles(raw: list[dict | list], symbol: str, timeframe: str) -> list[Candle]:
    """Transform raw Upstox candle rows into validated Candle models.

    Args:
        raw: Raw candle rows from Upstox payload.
        symbol: Instrument symbol for all rows.
        timeframe: Candle timeframe string.

    Returns:
        Candle list sorted in ascending timestamp order.

    Raises:
        InvalidCandleError: If row format, timestamp, or OHLCV values are invalid.
    """
    transformed: list[Candle] = []
    for index, row in enumerate(raw):
        values = _extract_values(row, index)
        timestamp = _parse_timestamp(values[0], index)
        ohlcv = _parse_positive_ohlcv(values[1:6], index)

        transformed.append(
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=timestamp,
                open=ohlcv[0],
                high=ohlcv[1],
                low=ohlcv[2],
                close=ohlcv[3],
                volume=ohlcv[4],
            )
        )

    return sorted(transformed, key=lambda candle: candle.timestamp)


def _extract_values(row: dict | list, index: int) -> list:
    """Extract ordered candle values from one raw row."""
    if not isinstance(row, list):
        msg = f"Invalid candle row at index {index}: expected list format."
        raise InvalidCandleError(msg)

    if len(row) != _UPSTOX_CANDLE_ROW_LENGTH:
        msg = (
            f"Invalid candle row at index {index}: expected "
            f"{_UPSTOX_CANDLE_ROW_LENGTH} fields, got {len(row)}."
        )
        raise InvalidCandleError(msg)

    return row


def _parse_timestamp(value: object, index: int) -> datetime:
    """Parse and normalize timestamp to IST."""
    if not isinstance(value, str):
        msg = f"Invalid candle timestamp at index {index}: expected ISO8601 string."
        raise InvalidCandleError(msg)

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        msg = f"Invalid candle timestamp at index {index}: {value!r}."
        raise InvalidCandleError(msg) from exc

    try:
        return to_ist(parsed)
    except ValueError as exc:
        msg = f"Invalid candle timestamp at index {index}: timezone-aware timestamp required."
        raise InvalidCandleError(msg) from exc


def _parse_positive_ohlcv(values: list[object], index: int) -> tuple[float, float, float, float, float]:
    """Parse and validate OHLCV values as positive floats."""
    parsed: list[float] = []
    for value in values:
        if not isinstance(value, Real) or isinstance(value, bool) or value <= 0:
            msg = f"Invalid OHLCV values at index {index}: values must be positive numbers."
            raise InvalidCandleError(msg)
        parsed.append(float(value))

    return parsed[0], parsed[1], parsed[2], parsed[3], parsed[4]
