"""High-level backtest orchestration and execution."""

from __future__ import annotations

import logging
import sqlite3
import uuid
from datetime import date

from src.engine.executor import execute_backtest
from src.models.backtest_config import BacktestConfig
from src.models.simulation_result import SimulationResult

logger = logging.getLogger(__name__)


def run_backtest(
    symbol: str,
    start_date: date,
    end_date: date,
    config_dict: dict,
    db_path: str,
) -> SimulationResult:
    """Execute a complete backtest with configuration validation.

    Orchestrates the full pipeline: validate config, open database,
    execute backtest, return results.

    Args:
        symbol: Instrument symbol to backtest.
        start_date: Inclusive start date for candle range.
        end_date: Inclusive end date for candle range.
        config_dict: Configuration dictionary (charges, risk, ATR params, etc.).
        db_path: Path to SQLite database file.

    Returns:
        SimulationResult with completed trades and rejected trades.

    Raises:
        ValueError: If config is invalid.
        ExecutionError: If backtest execution fails at any stage.
    """
    run_id = str(uuid.uuid4())
    logger.info(f"Starting backtest run {run_id} for {symbol} ({start_date} to {end_date})")

    config_with_dates = {**config_dict, "start_date": start_date, "end_date": end_date}
    config = BacktestConfig.from_dict(config_with_dates, run_id=run_id, symbol=symbol)
    logger.info(f"Config validated: capital={config.initial_capital}, risk={config.risk_per_trade_pct*100}%")

    conn = None
    try:
        conn = sqlite3.connect(db_path)
        logger.info(f"Connected to database: {db_path}")

        result = execute_backtest(symbol, start_date, end_date, config, conn)

        logger.info(
            f"Run {run_id} complete: {len(result.trades)} trades, "
            f"{len(result.rejected_trades)} rejected"
        )
        return result

    finally:
        if conn is not None:
            conn.close()
            logger.info(f"Database connection closed for run {run_id}")
