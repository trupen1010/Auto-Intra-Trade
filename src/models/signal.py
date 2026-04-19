"""Domain model for computed signal states."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from src.utils.enums import SignalSide, Timeframe

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
class SignalState:
    """Represents one closed-candle signal state."""

    symbol: str
    timeframe: str
    candle_close_time: datetime
    side: SignalSide
    trailing_stop: float | None
    close_price: float

    def __post_init__(self) -> None:
        """Validate signal state fields after initialization.

        Raises:
            ValueError: If timeframe is unsupported or datetime is invalid.
        """
        valid_timeframes = {tf.value for tf in Timeframe}
        if self.timeframe not in valid_timeframes:
            raise ValueError(f"Unsupported timeframe: {self.timeframe}")

        _validate_ist_datetime(self.candle_close_time, "candle_close_time")
