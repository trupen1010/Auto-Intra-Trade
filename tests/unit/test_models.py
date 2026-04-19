"""Unit tests for domain and config models."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from src.models.candle import Candle
from src.models.config_models import ChargesConfig, ExecutionConfig
from src.models.trade import Trade
from src.utils.enums import EntryTF, TradeSide

IST = ZoneInfo("Asia/Kolkata")


def test_candle_rejects_naive_datetime() -> None:
    """Candle raises when timestamp is timezone-naive."""
    with pytest.raises(ValueError, match="timezone-aware Asia/Kolkata"):
        Candle(
            symbol="RELIANCE",
            timeframe="5m",
            timestamp=datetime(2026, 4, 19, 9, 15),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000.0,
        )


def test_trade_defaults_are_correct() -> None:
    """Trade optional/default fields initialize to expected values."""
    now = datetime(2026, 4, 19, 9, 20, tzinfo=IST)
    trade = Trade(
        trade_id="T1",
        symbol="RELIANCE",
        side=TradeSide.LONG,
        entry_tf=EntryTF.FIVE_MINUTE,
        entry_signal_time=now,
        entry_time=now,
        entry_signal_price=100.0,
        entry_price=100.1,
        quantity=10,
        hard_stop_price=98.0,
    )

    assert trade.exit_signal_time is None
    assert trade.exit_time is None
    assert trade.exit_signal_price is None
    assert trade.exit_price is None
    assert trade.exit_reason is None
    assert trade.charges == 0.0
    assert trade.gross_pnl == 0.0
    assert trade.net_pnl == 0.0
    assert trade.capital_before_trade == 0.0
    assert trade.capital_after_trade == 0.0
    assert trade.state_1d_at_entry == ""
    assert trade.state_15m_at_entry == ""
    assert trade.state_5m_at_entry == ""


def test_charges_config_rejects_negative_values() -> None:
    """ChargesConfig rejects negative numeric values."""
    with pytest.raises(ValidationError):
        ChargesConfig(
            brokerage_cap_per_order=-1.0,
            brokerage_pct=0.0003,
            stt_sell_pct=0.001,
            transaction_pct=0.0000325,
            gst_pct=0.18,
            sebi_pct=0.000001,
            stamp_duty_buy_pct=0.00003,
        )


def test_execution_config_parses_time_strings_correctly() -> None:
    """ExecutionConfig parses HH:MM:SS strings into time objects."""
    config = ExecutionConfig(
        entry_model="next_open",
        exit_model="close_price",
        slippage_pct=0.0005,
        entry_cutoff_time="14:45:00",
        forced_exit_time="15:10:00",
        one_trade_at_a_time=True,
        same_candle_reentry_block=True,
    )

    assert config.entry_cutoff_time.hour == 14
    assert config.entry_cutoff_time.minute == 45
    assert config.forced_exit_time.hour == 15
    assert config.forced_exit_time.minute == 10
