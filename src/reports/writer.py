"""Write backtest results to CSV and JSON files."""

from __future__ import annotations

import csv
import json
import logging
from pathlib import Path

from src.models.backtest_config import BacktestConfig
from src.models.simulation_result import SimulationResult
from src.reports.summary_builder import build_summary
from src.reports.trade_formatter import format_rejected_trades, format_trades

logger = logging.getLogger(__name__)


def write_run_report(
    result: SimulationResult,
    config: BacktestConfig,
    base_dir: str = "data/reports",
) -> str:
    """Write backtest results to CSV and JSON files.

    Creates output directory {base_dir}/{run_id}/ and writes:
      - trades.csv: Closed trades with entry/exit details and PnL
      - rejected_trades.csv: Rejected entry attempts
      - summary.json: Run-level statistics
      - config_snapshot.json: Configuration snapshot (runtime arrays excluded)

    Args:
        result: SimulationResult from execute_backtest.
        config: BacktestConfig with run metadata.
        base_dir: Base directory for report output (default: "data/reports").

    Returns:
        The output directory path as a string.
    """
    output_dir = Path(base_dir) / config.run_id
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created output directory: {output_dir}")

    # Format trades and rejected trades.
    formatted_trades = format_trades(result.trades)
    formatted_rejected = format_rejected_trades(result.rejected_trades)

    # Write trades.csv
    trades_path = output_dir / "trades.csv"
    if formatted_trades:
        with open(trades_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=formatted_trades[0].keys())
            writer.writeheader()
            writer.writerows(formatted_trades)
        logger.info(f"Wrote {len(formatted_trades)} trades to {trades_path}")
    else:
        trades_path.touch()
        logger.info(f"No trades to write; created empty {trades_path}")

    # Write rejected_trades.csv
    rejected_path = output_dir / "rejected_trades.csv"
    if formatted_rejected:
        with open(rejected_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=formatted_rejected[0].keys())
            writer.writeheader()
            writer.writerows(formatted_rejected)
        logger.info(f"Wrote {len(formatted_rejected)} rejected trades to {rejected_path}")
    else:
        rejected_path.touch()
        logger.info(f"No rejected trades to write; created empty {rejected_path}")

    # Write summary.json
    summary = build_summary(formatted_trades, config)
    summary_path = output_dir / "summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    logger.info(f"Wrote summary to {summary_path}")

    # Write config_snapshot.json (exclude runtime arrays)
    config_snapshot = {
        "run_id": config.run_id,
        "symbol": config.symbol,
        "start_date": config.start_date.isoformat(),
        "end_date": config.end_date.isoformat(),
        "initial_capital": config.initial_capital,
        "risk_per_trade_pct": config.risk_per_trade_pct,
        "sl_atr_multiplier": config.sl_atr_multiplier,
        "atr_period": config.atr_period,
        "atr_sensitivity": config.atr_sensitivity,
        "entry_cutoff_time": config.entry_cutoff_time.isoformat(),
        "session_end_time": config.session_end_time.isoformat(),
        "charges": {
            "brokerage_pct": config.charges.brokerage_pct,
            "brokerage_cap_per_order": config.charges.brokerage_cap_per_order,
            "stt_sell_pct": config.charges.stt_sell_pct,
            "transaction_pct": config.charges.transaction_pct,
            "sebi_pct": config.charges.sebi_pct,
            "gst_pct": config.charges.gst_pct,
            "stamp_duty_buy_pct": config.charges.stamp_duty_buy_pct,
        },
    }
    config_path = output_dir / "config_snapshot.json"
    with open(config_path, "w") as f:
        json.dump(config_snapshot, f, indent=2)
    logger.info(f"Wrote config snapshot to {config_path}")

    logger.info(f"Report generation complete for run {config.run_id}")
    return str(output_dir)
