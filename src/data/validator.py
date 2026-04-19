"""Candle sequence validation for transformed OHLCV data."""

from __future__ import annotations

from datetime import datetime, timedelta

from src.models.candle import Candle
from src.utils.datetime_utils import is_market_hours, is_same_session
from src.utils.exceptions import DataGapError, InsufficientDataError, InvalidCandleError

_INTRADAY_GAP_LIMITS = {
    "5m": timedelta(minutes=5),
    "15m": timedelta(minutes=15),
}


def validate_candle_sequence(candles: list[Candle], timeframe: str, symbol: str) -> None:
    """Validate sequence integrity and market-session continuity for candles.

    Args:
        candles: Chronological candle list to validate.
        timeframe: Timeframe string corresponding to the candle list.
        symbol: Instrument symbol used in validation error details.

    Raises:
        InsufficientDataError: If fewer than two candles are provided.
        InvalidCandleError: If sequence ordering, duplicates, or market hours fail.
        DataGapError: If an intraday sequence has a gap larger than allowed.
    """
    if len(candles) < 2:
        msg = f"Insufficient candles for symbol '{symbol}' on timeframe '{timeframe}': minimum 2 required."
        raise InsufficientDataError(msg)

    _validate_symbol_and_timeframe(candles, timeframe, symbol)
    _validate_chronological_order(candles, timeframe, symbol)
    _validate_duplicate_timestamps(candles, timeframe, symbol)
    _validate_market_hours(candles, timeframe, symbol)
    _validate_intraday_gaps(candles, timeframe, symbol)


def _validate_symbol_and_timeframe(candles: list[Candle], timeframe: str, symbol: str) -> None:
    """Ensure each candle matches the expected symbol and timeframe."""
    for candle in candles:
        if candle.symbol != symbol:
            msg = (
                f"Candle symbol mismatch for validation on timeframe '{timeframe}': "
                f"expected '{symbol}', got '{candle.symbol}'."
            )
            raise InvalidCandleError(msg)

        if candle.timeframe != timeframe:
            msg = (
                f"Candle timeframe mismatch for symbol '{symbol}': "
                f"expected '{timeframe}', got '{candle.timeframe}'."
            )
            raise InvalidCandleError(msg)


def _validate_chronological_order(candles: list[Candle], timeframe: str, symbol: str) -> None:
    """Ensure candle timestamps never move backward."""
    previous = candles[0].timestamp
    for candle in candles[1:]:
        if candle.timestamp < previous:
            msg = (
                f"Out-of-order candle sequence for symbol '{symbol}' on timeframe '{timeframe}': "
                f"{candle.timestamp.isoformat()} appears before {previous.isoformat()}."
            )
            raise InvalidCandleError(msg)
        previous = candle.timestamp


def _validate_duplicate_timestamps(candles: list[Candle], timeframe: str, symbol: str) -> None:
    """Ensure no duplicate candle timestamps exist."""
    seen: set[datetime] = set()
    for candle in candles:
        if candle.timestamp in seen:
            msg = (
                f"Duplicate candle timestamp for symbol '{symbol}' on timeframe '{timeframe}': "
                f"{candle.timestamp.isoformat()}."
            )
            raise InvalidCandleError(msg)
        seen.add(candle.timestamp)


def _validate_market_hours(candles: list[Candle], timeframe: str, symbol: str) -> None:
    """Validate session hours for intraday candles."""
    if timeframe == "1d":
        return

    for candle in candles:
        if not is_market_hours(candle.timestamp):
            msg = (
                f"Candle outside market hours for symbol '{symbol}' on timeframe '{timeframe}': "
                f"{candle.timestamp.isoformat()}."
            )
            raise InvalidCandleError(msg)


def _validate_intraday_gaps(candles: list[Candle], timeframe: str, symbol: str) -> None:
    """Detect first invalid gap for intraday candles."""
    max_gap = _INTRADAY_GAP_LIMITS.get(timeframe)
    if max_gap is None:
        return

    for previous, current in zip(candles, candles[1:]):
        if not is_same_session(previous.timestamp, current.timestamp):
            continue
        gap = current.timestamp - previous.timestamp
        if gap > max_gap:
            msg = (
                f"Data gap detected for symbol '{symbol}' on timeframe '{timeframe}': "
                f"{previous.timestamp.isoformat()} -> {current.timestamp.isoformat()} "
                f"({int(gap.total_seconds() // 60)} minutes)."
            )
            raise DataGapError(msg)
