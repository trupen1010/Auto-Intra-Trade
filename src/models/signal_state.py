"""Domain model for fresh transition-based signal detection."""

from __future__ import annotations

from dataclasses import dataclass

from src.utils.enums import SignalSide


@dataclass(frozen=True, slots=True)
class SignalTransition:
    """Represents signal side state for one bar with transition metadata.

    Attributes:
        side: Signal side on this bar.
        is_fresh: True only when this bar side differs from previous bar side.
        bar_index: Zero-based bar index in the evaluated series.
    """

    side: SignalSide
    is_fresh: bool
    bar_index: int
