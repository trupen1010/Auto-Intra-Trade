"""Domain model for multi-timeframe signal alignment."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.utils.datetime_utils import validate_ist_datetime
from src.utils.enums import SignalSide


@dataclass(frozen=True, slots=True)
class MtfAlignment:
    """Represents 1D bias and 15m signal alignment as of a 5m timestamp.

    Attributes:
        bias_1d: Most recent 1D signal side from a fully closed bar
            (``close_time <= as_of``).
        signal_15m: Most recent 15m signal side from a fully closed bar
            (``close_time <= as_of``).
        aligned: True when both sides match and are non-neutral.
        as_of: The 5m timestamp used for resolving state.
    """

    bias_1d: SignalSide
    signal_15m: SignalSide
    aligned: bool
    as_of: datetime

    def __post_init__(self) -> None:
        """Validate timezone-aware Asia/Kolkata timestamp."""

        validate_ist_datetime(self.as_of, "as_of")

