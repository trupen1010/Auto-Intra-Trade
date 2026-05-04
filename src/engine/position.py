"""Mutable open position state.

The simulation loop will hold an :class:`~src.engine.position.OpenPosition`
instance while a trade is active. When exiting, it is converted into an
immutable :class:`~src.models.trade.Trade` with exit fields populated.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from src.models.trade import Trade
from src.utils.datetime_utils import validate_ist_datetime
from src.utils.enums import ExitReason, SignalSide


@dataclass(slots=True)
class OpenPosition:
    """Represents an active position during simulation."""

    trade: Trade
    current_stop: float
    bars_held: int = 0

    def to_closed_trade(
        self,
        exit_time: datetime,
        exit_price: float,
        exit_reason: ExitReason,
        charges_pct: float,
    ) -> Trade:
        """Return a new immutable trade with exit + PnL computed.

        Args:
            exit_time: Time at which position is exited.
            exit_price: Executed exit price.
            exit_reason: Reason for closing.
            charges_pct: Percent charge applied to notional turnover.

        Returns:
            A new :class:`~src.models.trade.Trade` instance with exit fields.

        Raises:
            ValueError: If any inputs are invalid.
        """
        validate_ist_datetime(exit_time, "exit_time")
        exit_reason = ExitReason(exit_reason)
        if charges_pct < 0:
            raise ValueError("charges_pct must be non-negative")

        pnl_points = (
            exit_price - self.trade.entry_price
            if self.trade.direction == SignalSide.BUY
            else self.trade.entry_price - exit_price
        )
        pnl_rupees = pnl_points * float(self.trade.quantity)

        notional = (self.trade.entry_price + exit_price) * float(self.trade.quantity)
        charges = charges_pct * notional
        net_pnl = pnl_rupees - charges

        return Trade(
            run_id=self.trade.run_id,
            symbol=self.trade.symbol,
            timeframe_entry=self.trade.timeframe_entry,
            direction=self.trade.direction,
            entry_time=self.trade.entry_time,
            entry_price=self.trade.entry_price,
            quantity=self.trade.quantity,
            hard_sl=self.trade.hard_sl,
            exit_time=exit_time,
            exit_price=exit_price,
            exit_reason=exit_reason,
            pnl_points=pnl_points,
            pnl_rupees=pnl_rupees,
            charges=charges,
            net_pnl=net_pnl,
        )
