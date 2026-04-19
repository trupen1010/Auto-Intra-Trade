"""Domain model for validated OHLCV candles."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.utils.datetime_utils import validate_ist_datetime
from src.utils.enums import Timeframe


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

        validate_ist_datetime(self.timestamp, "timestamp")
