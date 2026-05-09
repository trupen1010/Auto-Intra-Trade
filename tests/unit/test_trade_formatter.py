"""Unit tests for trade formatter."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from src.engine.trade_state import EngineTradeState
from src.models.rejected_trade import RejectedTrade
from src.reports.trade_formatter import format_rejected_trades, format_trades
from src.utils.enums import EntryTF, ExitReason, SignalSide

IST = ZoneInfo("Asia/Kolkata")


@pytest.fixture
def buy_trade() -> EngineTradeState:
    """Create a profitable BUY trade."""
    entry_time = datetime(2024, 1, 15, 10, 0, tzinfo=IST)
    exit_time = datetime(2024, 1, 15, 11, 0, tzinfo=IST)
    return EngineTradeState(
        run_id="test_run",
        symbol="SBIN",
        timeframe_entry=EntryTF.FIVE_MINUTE,
        direction=SignalSide.BUY,
        entry_time=entry_time,
        entry_price=500.0,
        quantity=10,
        hard_sl=490.0,
        exit_time=exit_time,
        exit_price=510.0,
        exit_reason=ExitReason.SIGNAL_5M,
        pnl_points=10.0,  # 510 - 500
        pnl_rupees=100.0,  # 10 * 10
        charges=20.0,
        net_pnl=80.0,  # 100 - 20
    )


@pytest.fixture
def sell_trade() -> EngineTradeState:
    """Create a profitable SHORT trade."""
    entry_time = datetime(2024, 1, 15, 12, 0, tzinfo=IST)
    exit_time = datetime(2024, 1, 15, 13, 0, tzinfo=IST)
    return EngineTradeState(
        run_id="test_run",
        symbol="SBIN",
        timeframe_entry=EntryTF.FIFTEEN_MINUTE,
        direction=SignalSide.SELL,
        entry_time=entry_time,
        entry_price=500.0,
        quantity=20,
        hard_sl=510.0,
        exit_time=exit_time,
        exit_price=490.0,
        exit_reason=ExitReason.HARD_SL,
        pnl_points=10.0,  # 500 - 490
        pnl_rupees=200.0,  # 10 * 20
        charges=30.0,
        net_pnl=170.0,  # 200 - 30
    )


@pytest.fixture
def rejected_trade() -> RejectedTrade:
    """Create a rejected trade attempt."""
    timestamp = datetime(2024, 1, 15, 10, 30, tzinfo=IST)
    return RejectedTrade(
        symbol="SBIN",
        timestamp=timestamp,
        timeframe="5m",
        requested_side="LONG",
        reason="quantity=0",
    )


class TestFormatTrades:
    """Tests for format_trades function."""

    def test_format_trades_buy_pnl_correct(self, buy_trade: EngineTradeState) -> None:
        """Test that BUY trade PnL is calculated correctly."""
        formatted = format_trades([buy_trade])
        assert len(formatted) == 1

        row = formatted[0]
        assert row["direction"] == "LONG"
        assert row["gross_pnl"] == 100.0
        assert row["charges"] == 20.0
        assert row["net_pnl"] == 80.0

    def test_format_trades_sell_pnl_correct(self, sell_trade: EngineTradeState) -> None:
        """Test that SELL trade PnL is calculated correctly."""
        formatted = format_trades([sell_trade])
        assert len(formatted) == 1

        row = formatted[0]
        assert row["direction"] == "SHORT"
        assert row["gross_pnl"] == 200.0
        assert row["charges"] == 30.0
        assert row["net_pnl"] == 170.0

    def test_format_trades_fields_present(self, buy_trade: EngineTradeState) -> None:
        """Test that all expected fields are present in formatted output."""
        formatted = format_trades([buy_trade])
        row = formatted[0]

        expected_fields = {
            "run_id",
            "symbol",
            "direction",
            "timeframe_entry",
            "entry_time",
            "exit_time",
            "entry_price",
            "exit_price",
            "quantity",
            "gross_pnl",
            "charges",
            "net_pnl",
            "hard_sl",
            "exit_reason",
        }
        assert set(row.keys()) == expected_fields

    def test_format_trades_timestamps_iso8601(self, buy_trade: EngineTradeState) -> None:
        """Test that timestamps are ISO8601 strings."""
        formatted = format_trades([buy_trade])
        row = formatted[0]

        assert isinstance(row["entry_time"], str)
        assert isinstance(row["exit_time"], str)
        assert "T" in row["entry_time"]
        assert "T" in row["exit_time"]

    def test_format_trades_multiple_trades(
        self, buy_trade: EngineTradeState, sell_trade: EngineTradeState
    ) -> None:
        """Test formatting multiple trades."""
        formatted = format_trades([buy_trade, sell_trade])
        assert len(formatted) == 2
        assert formatted[0]["direction"] == "LONG"
        assert formatted[1]["direction"] == "SHORT"

    def test_format_trades_empty_list(self) -> None:
        """Test formatting empty trade list."""
        formatted = format_trades([])
        assert formatted == []


class TestFormatRejectedTrades:
    """Tests for format_rejected_trades function."""

    def test_format_rejected_trades_fields_present(self, rejected_trade: RejectedTrade) -> None:
        """Test that all expected fields are present."""
        formatted = format_rejected_trades([rejected_trade])
        assert len(formatted) == 1

        row = formatted[0]
        expected_fields = {"symbol", "timestamp", "timeframe", "requested_side", "reason"}
        assert set(row.keys()) == expected_fields

    def test_format_rejected_trades_values_correct(self, rejected_trade: RejectedTrade) -> None:
        """Test that field values are correct."""
        formatted = format_rejected_trades([rejected_trade])
        row = formatted[0]

        assert row["symbol"] == "SBIN"
        assert row["timeframe"] == "5m"
        assert row["requested_side"] == "LONG"
        assert row["reason"] == "quantity=0"

    def test_format_rejected_trades_timestamp_iso8601(self, rejected_trade: RejectedTrade) -> None:
        """Test that timestamp is ISO8601 string."""
        formatted = format_rejected_trades([rejected_trade])
        row = formatted[0]

        assert isinstance(row["timestamp"], str)
        assert "T" in row["timestamp"]

    def test_format_rejected_trades_multiple(self) -> None:
        """Test formatting multiple rejected trades."""
        rt1 = RejectedTrade(
            symbol="SBIN",
            timestamp=datetime(2024, 1, 15, 10, 0, tzinfo=IST),
            timeframe="5m",
            requested_side="LONG",
            reason="quantity=0",
        )
        rt2 = RejectedTrade(
            symbol="SBIN",
            timestamp=datetime(2024, 1, 15, 11, 0, tzinfo=IST),
            timeframe="15m",
            requested_side="SHORT",
            reason="entry past cutoff",
        )
        formatted = format_rejected_trades([rt1, rt2])
        assert len(formatted) == 2

    def test_format_rejected_trades_empty_list(self) -> None:
        """Test formatting empty rejected trade list."""
        formatted = format_rejected_trades([])
        assert formatted == []
