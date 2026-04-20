"""Unit tests for signal transition detection."""

from __future__ import annotations

from src.indicators.signals import detect_signals
from src.utils.enums import SignalSide


def test_first_bar_is_never_fresh() -> None:
    """Index 0 is never fresh because there is no previous state."""
    result = detect_signals([SignalSide.BUY])

    assert result[0].bar_index == 0
    assert result[0].is_fresh is False


def test_buy_transition_is_fresh() -> None:
    """A NEUTRAL -> BUY transition emits fresh signal on BUY bar."""
    result = detect_signals([SignalSide.NEUTRAL, SignalSide.BUY])

    assert result[1].side == SignalSide.BUY
    assert result[1].is_fresh is True


def test_sell_transition_is_fresh() -> None:
    """A BUY -> SELL transition emits fresh signal on SELL bar."""
    result = detect_signals([SignalSide.BUY, SignalSide.SELL])

    assert result[1].side == SignalSide.SELL
    assert result[1].is_fresh is True


def test_same_side_continuation_is_not_fresh() -> None:
    """Repeating the same side across bars is not fresh."""
    result = detect_signals([SignalSide.BUY, SignalSide.BUY, SignalSide.BUY])

    assert result[1].is_fresh is False
    assert result[2].is_fresh is False


def test_output_length_matches_input() -> None:
    """Output list length always matches input side list length."""
    sides = [SignalSide.NEUTRAL, SignalSide.BUY, SignalSide.SELL, SignalSide.SELL]
    result = detect_signals(sides)

    assert len(result) == len(sides)


def test_neutral_to_neutral_is_not_fresh() -> None:
    """A NEUTRAL -> NEUTRAL continuation is not fresh."""
    result = detect_signals([SignalSide.NEUTRAL, SignalSide.NEUTRAL])

    assert result[1].is_fresh is False
