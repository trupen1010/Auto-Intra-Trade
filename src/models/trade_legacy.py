"""Legacy trade models for SQLite persistence.

These models were generated earlier in the repository history for persisting
trades to SQLite.

The baseline engine's simulation layer now uses `src.models.trade.Trade` as a
simplified immutable trade state model (run_id + direction + entry/exit).
SQLite persistence will be revisited later in the generation sequence.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.utils.datetime_utils import validate_ist_datetime
from src.utils.enums import EntryTF, ExitReason, TradeSide


@dataclass(slots=True)
class Trade:
    """Represents one full trade lifecycle in the earlier persistence layer."""

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
        try:
            self.side = TradeSide(self.side)
        except ValueError as exc:
            raise ValueError(f"Unsupported trade side: {self.side}") from exc

        try:
            self.entry_tf = EntryTF(self.entry_tf)
        except ValueError as exc:
            raise ValueError(f"Unsupported entry timeframe: {self.entry_tf}") from exc

        if self.exit_reason is not None:
            try:
                self.exit_reason = ExitReason(self.exit_reason)
            except ValueError as exc:
                raise ValueError(f"Unsupported exit reason: {self.exit_reason}") from exc

        validate_ist_datetime(self.entry_signal_time, "entry_signal_time")
        validate_ist_datetime(self.entry_time, "entry_time")
        if self.exit_signal_time is not None:
            validate_ist_datetime(self.exit_signal_time, "exit_signal_time")
        if self.exit_time is not None:
            validate_ist_datetime(self.exit_time, "exit_time")


@dataclass(slots=True)
class RejectedTrade:
    """Represents a rejected trade attempt for the earlier persistence layer."""

    symbol: str
    timestamp: datetime
    timeframe: str
    requested_side: str
    reason: str

    def __post_init__(self) -> None:
        validate_ist_datetime(self.timestamp, "timestamp")
