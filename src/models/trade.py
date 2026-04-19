"""Domain models for executed and rejected trades."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

from src.utils.enums import EntryTF, ExitReason, Timeframe, TradeSide

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
class Trade:
    """Represents one full trade lifecycle in the backtest."""

    trade_id: str
    symbol: str
    side: TradeSide
    entry_tf: EntryTF
    entry_signal_time: datetime
    entry_time: datetime
    entry_signal_price: float
    entry_price: float
    quantity: int
    hard_stop_price: float
    exit_signal_time: datetime | None = None
    exit_time: datetime | None = None
    exit_signal_price: float | None = None
    exit_price: float | None = None
    exit_reason: ExitReason | None = None
    charges: float = 0.0
    gross_pnl: float = 0.0
    net_pnl: float = 0.0
    capital_before_trade: float = 0.0
    capital_after_trade: float = 0.0
    state_1d_at_entry: str = ""
    state_15m_at_entry: str = ""
    state_5m_at_entry: str = ""

    def __post_init__(self) -> None:
        """Validate datetime fields after initialization.

        Raises:
            ValueError: If any datetime field is invalid.
        """
        _validate_ist_datetime(self.entry_signal_time, "entry_signal_time")
        _validate_ist_datetime(self.entry_time, "entry_time")

        if self.exit_signal_time is not None:
            _validate_ist_datetime(self.exit_signal_time, "exit_signal_time")

        if self.exit_time is not None:
            _validate_ist_datetime(self.exit_time, "exit_time")


@dataclass(slots=True)
class RejectedTrade:
    """Represents a trade attempt rejected before entry."""

    symbol: str
    timestamp: datetime
    timeframe: str
    requested_side: str
    reason: str

    def __post_init__(self) -> None:
        """Validate rejected trade fields after initialization.

        Raises:
            ValueError: If timeframe is unsupported or timestamp is invalid.
        """
        valid_timeframes = {tf.value for tf in Timeframe}
        if self.timeframe not in valid_timeframes:
            raise ValueError(f"Unsupported timeframe: {self.timeframe}")

        _validate_ist_datetime(self.timestamp, "timestamp")
