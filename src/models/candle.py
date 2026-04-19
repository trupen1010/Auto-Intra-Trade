"""Domain model for validated OHLCV candles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from src.utils.enums import Timeframe

IST = ZoneInfo("Asia/Kolkata")


def _validate_ist_datetime(value: datetime, field_name: str) -> None:
    """Validate that a datetime value is timezone-aware Asia/Kolkata.

    Args:
        value: Datetime value to validate.
        field_name: Name of the field being validated.

    Raises:
        ValueError: If datetime is naive or not Asia/Kolkata timezone.
    """
    if value.tzinfo is None:
        raise ValueError(f"{field_name} must be timezone-aware Asia/Kolkata datetime.")

    if getattr(value.tzinfo, "key", None) != IST.key:
        raise ValueError(f"{field_name} must be timezone-aware Asia/Kolkata datetime.")


@dataclass(slots=True)
class Candle:
    """Represents one validated market candle."""

    symbol: str
    timeframe: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self) -> None:
        """Validate candle fields after initialization.

        Raises:
            ValueError: If timeframe is unsupported or timestamp is invalid.
        """
        valid_timeframes = {tf.value for tf in Timeframe}
        if self.timeframe not in valid_timeframes:
            raise ValueError(f"Unsupported timeframe: {self.timeframe}")

        _validate_ist_datetime(self.timestamp, "timestamp")
