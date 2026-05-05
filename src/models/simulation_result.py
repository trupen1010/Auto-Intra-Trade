"""Simulation output container.

The simulator returns engine-internal trade state objects along with any
rejected trade attempts, plus a run identifier.
"""

from __future__ import annotations

from dataclasses import dataclass

from src.engine.trade_state import EngineTradeState
from src.models.rejected_trade import RejectedTrade


@dataclass(frozen=True, slots=True)
class SimulationResult:
    """Holds the result of a candle-by-candle simulation run.

    Attributes:
        trades: Completed trades captured during the simulation.
        rejected_trades: Rejected trade attempts (e.g. quantity = 0).
        run_id: Unique backtest run identifier.
    """

    trades: list[EngineTradeState]
    rejected_trades: list[RejectedTrade]
    run_id: str

