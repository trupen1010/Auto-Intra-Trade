"""Documented domain Trade model.

This module contains the canonical :class:`Trade` dataclass used for
persistence (SQLite) and reporting throughout the backtest engine.

For the lightweight engine-internal trade state used during the simulation
loop see :class:`~src.engine.trade_state.EngineTradeState`.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.utils.datetime_utils import validate_ist_datetime
from src.utils.enums import EntryTF, ExitReason, TradeSide


@dataclass(slots=True)
class Trade:
    """Represents one full trade lifecycle in the persistence layer.

    Attributes:
        trade_id: Unique identifier for the trade, scoped to a run.
        symbol: Instrument symbol.
        side: LONG or SHORT.
        entry_tf: Timeframe that originated the entry signal.
        entry_signal_time: Candle close time when entry signal fired.
        entry_time: Actual execution time of entry.
        entry_signal_price: Close price at the entry signal candle.
        entry_price: Executed entry price (post-slippage).
        quantity: Number of shares/units traded.
        hard_stop_price: Hard stop-loss price computed at entry.
        exit_signal_time: Candle close time when exit signal fired.
        exit_time: Actual execution time of exit.
        exit_signal_price: Close price at the exit signal candle.
        exit_price: Executed exit price (post-slippage).
        exit_reason: Reason the trade was closed.
        charges: Total round-trip charges in rupees.
        gross_pnl: Gross profit/loss before charges.
        net_pnl: Net profit/loss after charges.
        capital_before_trade: Available capital before this trade.
        capital_after_trade: Available capital after this trade.
        state_1d_at_entry: 1D signal state string captured at entry.
        state_15m_at_entry: 15m signal state string captured at entry.
        state_5m_at_entry: 5m signal state string captured at entry.
    """

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
        """Validate and coerce enum fields after initialization.

        Raises:
            ValueError: If any constrained field is invalid.
        """
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

