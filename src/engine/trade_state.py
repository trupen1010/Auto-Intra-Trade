"""Engine-internal trade state models.

These lightweight immutable dataclasses are used exclusively by the
simulation loop.  They are distinct from the persistence-layer
:class:`~src.models.trade.Trade` and :class:`~src.models.rejected_trade.RejectedTrade`
models, which include additional fields required for SQLite storage and
reporting.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.utils.datetime_utils import validate_ist_datetime
from src.utils.enums import EntryTF, ExitReason, SignalSide


def _coerce_or_none[T](enum_cls: type[T], value: object | None) -> T | None:
    """Coerce an optional value to an enum, returning None if value is None."""
    if value is None:
        return None
    return enum_cls(value)  # type: ignore[call-arg]


@dataclass(frozen=True, slots=True)
class EngineTradeState:
    """Lightweight immutable trade record used inside the simulation loop.

    Created at entry and replaced (not mutated) with exit fields populated
    when the position is closed via
    :meth:`~src.engine.position.OpenPosition.to_closed_trade`.

    Attributes:
        run_id: Unique backtest run identifier.
        symbol: Instrument symbol.
        timeframe_entry: Timeframe that originated the entry signal.
        direction: BUY or SELL signal that triggered this trade.
        entry_time: IST-aware execution time of entry.
        entry_price: Executed entry price (post-slippage).
        quantity: Number of shares/units.
        hard_sl: Hard stop-loss price computed at entry.
        exit_time: IST-aware execution time of exit (None while open).
        exit_price: Executed exit price (None while open).
        exit_reason: Reason the trade was closed (None while open).
        pnl_points: Price difference in the favourable direction (None while open).
        pnl_rupees: ``pnl_points * quantity`` (None while open).
        charges: Round-trip charges in rupees (None while open).
        net_pnl: ``pnl_rupees - charges`` (None while open).
    """

    run_id: str
    symbol: str
    timeframe_entry: EntryTF
    direction: SignalSide
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
        """Validate and coerce enum fields after initialization.

        Raises:
            ValueError: If any constrained field is invalid.
        """
        try:
            object.__setattr__(self, "timeframe_entry", EntryTF(self.timeframe_entry))
        except ValueError as exc:
            raise ValueError(f"Unsupported entry timeframe: {self.timeframe_entry}") from exc

        try:
            object.__setattr__(self, "direction", SignalSide(self.direction))
        except ValueError as exc:
            raise ValueError(f"Unsupported direction: {self.direction}") from exc

        try:
            object.__setattr__(
                self, "exit_reason", _coerce_or_none(ExitReason, self.exit_reason)
            )
        except ValueError as exc:
            raise ValueError(f"Unsupported exit reason: {self.exit_reason}") from exc

        validate_ist_datetime(self.entry_time, "entry_time")
        if self.exit_time is not None:
            validate_ist_datetime(self.exit_time, "exit_time")


@dataclass(frozen=True, slots=True)
class EngineRejectedTrade:
    """Engine-internal record of a rejected trade attempt.

    Captured by the simulation loop when an entry signal cannot be acted
    on (e.g. quantity = 0, entry past cutoff time).  For the persistence-
    layer equivalent see :class:`~src.models.rejected_trade.RejectedTrade`.

    Attributes:
        run_id: Unique backtest run identifier.
        symbol: Instrument symbol.
        signal_time: IST-aware time of the rejected entry signal.
        direction: Signal side that was rejected.
        reason: Human-readable reason for the rejection.
    """

    run_id: str
    symbol: str
    signal_time: datetime
    direction: SignalSide
    reason: str

    def __post_init__(self) -> None:
        """Validate fields after initialization.

        Raises:
            ValueError: If signal_time is not IST-aware or direction is invalid.
        """
        validate_ist_datetime(self.signal_time, "signal_time")
        try:
            object.__setattr__(self, "direction", SignalSide(self.direction))
        except ValueError as exc:
            raise ValueError(f"Unsupported direction: {self.direction}") from exc
