"""Format engine trade states for reporting output."""

from __future__ import annotations

from src.engine.trade_state import EngineTradeState
from src.models.rejected_trade import RejectedTrade
from src.utils.enums import SignalSide, TradeSide


def format_trades(trades: list[EngineTradeState]) -> list[dict]:
    """Convert closed trades to flat dictionary rows for CSV export.

    Each row contains entry/exit details, PnL, charges, capital snapshots,
    and exit reason. Timestamps are ISO8601 strings in IST timezone.

    Args:
        trades: List of closed EngineTradeState objects.

    Returns:
        List of dictionaries, one per trade, suitable for csv.DictWriter.
    """
    rows = []
    for trade in trades:
        direction_str = "LONG" if trade.direction == SignalSide.BUY else "SHORT"
        row = {
            "run_id": trade.run_id,
            "symbol": trade.symbol,
            "direction": direction_str,
            "timeframe_entry": trade.timeframe_entry.value,
            "entry_time": trade.entry_time.isoformat(),
            "exit_time": trade.exit_time.isoformat() if trade.exit_time else "",
            "entry_price": round(trade.entry_price, 2),
            "exit_price": round(trade.exit_price, 2) if trade.exit_price else None,
            "quantity": trade.quantity,
            "gross_pnl": round(trade.pnl_rupees, 2) if trade.pnl_rupees is not None else 0,
            "charges": round(trade.charges, 2) if trade.charges is not None else 0,
            "net_pnl": round(trade.net_pnl, 2) if trade.net_pnl is not None else 0,
            "hard_sl": round(trade.hard_sl, 2),
            "exit_reason": trade.exit_reason.value if trade.exit_reason else "",
            "capital_before_trade": (
                round(trade.capital_before_trade, 2)
                if trade.capital_before_trade is not None
                else None
            ),
            "capital_after_trade": (
                round(trade.capital_after_trade, 2)
                if trade.capital_after_trade is not None
                else None
            ),
        }
        rows.append(row)
    return rows


def format_rejected_trades(rejected: list[RejectedTrade]) -> list[dict]:
    """Convert rejected trade attempts to flat dictionary rows for CSV export.

    Args:
        rejected: List of RejectedTrade objects.

    Returns:
        List of dictionaries, one per rejected attempt, suitable for csv.DictWriter.
    """
    rows = []
    for rt in rejected:
        row = {
            "symbol": rt.symbol,
            "timestamp": rt.timestamp.isoformat(),
            "timeframe": rt.timeframe,
            "requested_side": rt.requested_side,
            "reason": rt.reason,
        }
        rows.append(row)
    return rows
