"""Trade state model.

This module intentionally contains only the immutable trade dataclass used by
the engine. Simulation logic lives elsewhere.

Note:
    A previous version of this repository had a different `Trade` model used for
    database persistence (with `trade_id`, `TradeSide`, etc.). Step 12 introduces
    the baseline engine's simplified `Trade` state model used by the simulation
    loop.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.utils.datetime_utils import validate_ist_datetime
from src.utils.enums import ExitReason, SignalSide


@dataclass(frozen=True, slots=True)
class RejectedTrade:
    """Represents a rejected trade attempt."""

    run_id: str
    symbol: str
    signal_time: datetime
    direction: SignalSide
    reason: str

    def __post_init__(self) -> None:
        validate_ist_datetime(self.signal_time, "signal_time")
        try:
            object.__setattr__(self, "direction", SignalSide(self.direction))
        except ValueError as exc:
            raise ValueError(f"Unsupported direction: {self.direction}") from exc


def _coerce_or_none[T](enum_cls: type[T], value: object | None) -> T | None:
    if value is None:
        return None
    return enum_cls(value)  # type: ignore[call-arg]


@dataclass(frozen=True, slots=True)
class Trade:
    """Represents a trade for a single symbol within one run."""

    run_id: str
    symbol: str
    timeframe_entry: str  # "5m" or "15m"
    direction: SignalSide  # BUY or SELL
    entry_time: datetime
    entry_price: float
    quantity: int
    hard_sl: float
    exit_time: datetime | None = None
    exit_price: float | None = None
    exit_reason: ExitReason | None = None
    pnl_points: float | None = None
    pnl_rupees: float | None = None
    charges: float | None = None
    net_pnl: float | None = None

    def __post_init__(self) -> None:
        """Validate fields after initialization.

        Raises:
            ValueError: If any constrained field is invalid.
        """
        if self.timeframe_entry not in {"5m", "15m"}:
            raise ValueError(f"Unsupported entry timeframe: {self.timeframe_entry}")

        try:
            object.__setattr__(self, "direction", SignalSide(self.direction))
        except ValueError as exc:
            raise ValueError(f"Unsupported direction: {self.direction}") from exc

        try:
            object.__setattr__(self, "exit_reason", _coerce_or_none(ExitReason, self.exit_reason))
        except ValueError as exc:
            raise ValueError(f"Unsupported exit reason: {self.exit_reason}") from exc

        validate_ist_datetime(self.entry_time, "entry_time")
        if self.exit_time is not None:
            validate_ist_datetime(self.exit_time, "exit_time")
