"""Domain model for computed signal states."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.utils.datetime_utils import validate_ist_datetime
from src.utils.enums import SignalSide, Timeframe


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
        try:
            self.side = SignalSide(self.side)
        except ValueError as exc:
            raise ValueError(f"Unsupported signal side: {self.side}") from exc

        valid_timeframes = {tf.value for tf in Timeframe}
        if self.timeframe not in valid_timeframes:
            raise ValueError(f"Unsupported timeframe: {self.timeframe}")

        validate_ist_datetime(self.candle_close_time, "candle_close_time")
