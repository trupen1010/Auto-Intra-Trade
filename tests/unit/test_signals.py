"""Unit tests for signal transition detection."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import pytest

from src.indicators.signals import detect_signals, generate_signal_states
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


def test_generate_signal_states_emits_fresh_transitions() -> None:
    """Signal state output includes transition-based buy/sell flags."""
    tz = ZoneInfo("Asia/Kolkata")
    df = pd.DataFrame(
        {
            "timestamp": [
                datetime(2024, 1, 1, 9, 15, tzinfo=tz),
                datetime(2024, 1, 1, 9, 20, tzinfo=tz),
                datetime(2024, 1, 1, 9, 25, tzinfo=tz),
            ],
            "open": [100.0, 130.0, 90.0],
            "high": [110.0, 140.0, 95.0],
            "low": [90.0, 120.0, 85.0],
            "close": [100.0, 130.0, 90.0],
            "volume": [100.0, 110.0, 120.0],
            "symbol": ["TEST"] * 3,
            "timeframe": ["5m"] * 3,
        }
    )

    result = generate_signal_states(df, atr_period=2, sensitivity=1)

    assert list(result.columns) == [
        "timestamp",
        "close",
        "atr",
        "trailing_stop",
        "signal_side",
        "buy_signal",
        "sell_signal",
    ]
    assert result["signal_side"].tolist() == ["NEUTRAL", "NEUTRAL", "SELL"]
    assert result["buy_signal"].tolist() == [False, False, False]
    assert result["sell_signal"].tolist() == [False, False, True]


def test_generate_signal_states_requires_columns() -> None:
    """Missing required columns should raise a validation error."""
    tz = ZoneInfo("Asia/Kolkata")
    df = pd.DataFrame(
        {
            "timestamp": [datetime(2024, 1, 1, 9, 15, tzinfo=tz)],
            "open": [1.0],
            "high": [1.0],
            "low": [1.0],
        }
    )

    with pytest.raises(ValueError, match="Missing required columns"):
        generate_signal_states(df, atr_period=2, sensitivity=1)
