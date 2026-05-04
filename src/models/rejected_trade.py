"""Rejected trade model for persistence.

Represents trade attempts that were rejected before entering, stored for
auditing and analysis.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.utils.datetime_utils import validate_ist_datetime
from src.utils.enums import Timeframe


@dataclass(slots=True)
class RejectedTrade:
    """Represents a rejected trade attempt recorded for persistence.

    This model is used by the DB layer and reporting.  Engine-internal
    rejected trade records are held in :class:`~src.engine.trade_state.EngineRejectedTrade`.

    Attributes:
        symbol: Instrument symbol.
        timestamp: IST-aware time the rejection was recorded.
        timeframe: Candle timeframe that triggered the attempted entry.
        requested_side: Side that was requested (e.g. "LONG" or "SHORT").
        reason: Human-readable reason for the rejection.
    """

    symbol: str
    timestamp: datetime
    timeframe: str
    requested_side: str
    reason: str

    def __post_init__(self) -> None:
        """Validate fields after initialization.

        Raises:
            ValueError: If timeframe is unsupported or timestamp is not IST-aware.
        """
        validate_ist_datetime(self.timestamp, "timestamp")
        valid_timeframes = {tf.value for tf in Timeframe}
        if self.timeframe not in valid_timeframes:
            raise ValueError(f"Unsupported timeframe: {self.timeframe}")
