"""Project-wide enum definitions.

This module contains shared constrained values used across the backtest engine.
"""

from enum import StrEnum


class SignalSide(StrEnum):
    """Allowed signal states produced by indicator logic."""

    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


class TradeSide(StrEnum):
    """Allowed trade directions in the engine."""

    LONG = "LONG"
    SHORT = "SHORT"


class EntryTF(StrEnum):
    """Allowed timeframes that may originate a trade entry."""

    FIVE_MINUTE = "5m"
    FIFTEEN_MINUTE = "15m"


class ExitReason(StrEnum):
    """Allowed reasons for closing an active trade."""

    HARD_SL = "HARD_SL"
    TIME_EXIT = "TIME_EXIT"
    SIGNAL_5M = "SIGNAL_5M"
    SIGNAL_15M = "SIGNAL_15M"
    DATA_ERROR = "DATA_ERROR"
    SIGNAL_EXIT = "SIGNAL_EXIT"


class Timeframe(StrEnum):
    """Supported candle timeframes in the baseline engine."""

    FIVE_MINUTE = "5m"
    FIFTEEN_MINUTE = "15m"
    ONE_DAY = "1d"


class ExecutionModel(StrEnum):
    """Supported execution pricing models."""

    NEXT_OPEN = "next_open"
    CLOSE_PRICE = "close_price"
