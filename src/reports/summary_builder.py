"""Build run-level summary statistics from formatted trades."""

from __future__ import annotations

from src.models.backtest_config import BacktestConfig


def build_summary(
    trades: list[dict],
    config: BacktestConfig,
) -> dict:
    """Build a run-level summary from formatted trades and config.

    Calculates statistics including trade counts, PnL metrics, drawdown,
    and capital changes.

    Args:
        trades: List of formatted trade dictionaries (from format_trades).
        config: BacktestConfig with initial capital and run metadata.

    Returns:
        Dictionary with run-level summary metrics.
    """
    total_trades = len(trades)

    if total_trades == 0:
        return {
            "run_id": config.run_id,
            "symbol": config.symbol,
            "start_date": config.start_date.isoformat(),
            "end_date": config.end_date.isoformat(),
            "total_trades": 0,
            "winning_trades": 0,
            "losing_trades": 0,
            "win_rate_pct": 0.0,
            "gross_pnl": 0.0,
            "total_charges": 0.0,
            "net_pnl": 0.0,
            "max_drawdown": 0.0,
            "avg_trade_pnl": 0.0,
            "largest_win": 0.0,
            "largest_loss": 0.0,
            "initial_capital": round(config.initial_capital, 2),
            "final_capital": round(config.initial_capital, 2),
        }

    winning_trades = sum(1 for t in trades if t["net_pnl"] > 0)
    losing_trades = sum(1 for t in trades if t["net_pnl"] < 0)
    win_rate_pct = (winning_trades / total_trades * 100) if total_trades > 0 else 0.0

    gross_pnl = sum(t["gross_pnl"] for t in trades)
    total_charges = sum(t["charges"] for t in trades)
    net_pnl = sum(t["net_pnl"] for t in trades)

    # Calculate max drawdown: running cumulative peak, then max drop from peak.
    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for trade in trades:
        cumulative += trade["net_pnl"]
        if cumulative > peak:
            peak = cumulative
        drawdown = peak - cumulative
        if drawdown > max_drawdown:
            max_drawdown = drawdown

    avg_trade_pnl = net_pnl / total_trades if total_trades > 0 else 0.0
    largest_win = max((t["net_pnl"] for t in trades), default=0.0)
    largest_loss = min((t["net_pnl"] for t in trades), default=0.0)

    initial_capital = config.initial_capital
    final_capital = initial_capital + net_pnl

    return {
        "run_id": config.run_id,
        "symbol": config.symbol,
        "start_date": config.start_date.isoformat(),
        "end_date": config.end_date.isoformat(),
        "total_trades": total_trades,
        "winning_trades": winning_trades,
        "losing_trades": losing_trades,
        "win_rate_pct": round(win_rate_pct, 2),
        "gross_pnl": round(gross_pnl, 2),
        "total_charges": round(total_charges, 2),
        "net_pnl": round(net_pnl, 2),
        "max_drawdown": round(max_drawdown, 2),
        "avg_trade_pnl": round(avg_trade_pnl, 2),
        "largest_win": round(largest_win, 2),
        "largest_loss": round(largest_loss, 2),
        "initial_capital": round(initial_capital, 2),
        "final_capital": round(final_capital, 2),
    }
