"""Signal transition detection from trailing-stop side output."""

from __future__ import annotations

from src.models.signal_state import SignalState
from src.utils.enums import SignalSide


def detect_signals(sides: list[SignalSide]) -> list[SignalState]:
    """Detect fresh signal transitions from per-bar side states.

    A fresh signal is emitted only on bars where the side changes from the
    previous bar. Index 0 is never fresh because there is no prior state.

    Args:
        sides: Per-bar signal sides produced by trailing-stop computation.

    Returns:
        Signal states aligned 1:1 with ``sides`` containing transition flags.
    """
    states: list[SignalState] = []
    for idx, side in enumerate(sides):
        is_fresh = idx > 0 and sides[idx - 1] != side
        states.append(SignalState(side=side, is_fresh=is_fresh, bar_index=idx))
    return states
