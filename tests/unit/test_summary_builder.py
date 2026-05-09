"""Unit tests for summary builder."""

from __future__ import annotations

from datetime import date

import pytest

from src.models.backtest_config import BacktestConfig, ChargesConfig
from src.reports.summary_builder import build_summary


@pytest.fixture
def charges_config() -> ChargesConfig:
    """Standard charges configuration."""
    return ChargesConfig(
        brokerage_pct=0.0003,
        brokerage_cap_per_order=20.0,
        stt_sell_pct=0.00025,
        transaction_pct=0.0000345,
        sebi_pct=0.000001,
        gst_pct=0.18,
        stamp_duty_buy_pct=0.00003,
    )


@pytest.fixture
def config(charges_config: ChargesConfig) -> BacktestConfig:
    """Standard backtest configuration."""
    from datetime import time
    from zoneinfo import ZoneInfo

    return BacktestConfig(
        run_id="test_run",
        symbol="SBIN",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 1, 31),
        initial_capital=100_000.0,
        risk_per_trade_pct=0.01,
        sl_atr_multiplier=2.0,
        atr_period=14,
        atr_sensitivity=1,
        entry_cutoff_time=time(15, 0),
        session_end_time=time(15, 15),
        charges=charges_config,
    )


class TestBuildSummary:
    """Tests for build_summary function."""

    def test_summary_with_winning_trades(self, config: BacktestConfig) -> None:
        """Test summary calculation with winning trades."""
        trades = [
            {
                "run_id": "test_run",
                "symbol": "SBIN",
                "direction": "LONG",
                "timeframe_entry": "5m",
                "entry_time": "2024-01-15T10:00:00+05:30",
                "exit_time": "2024-01-15T11:00:00+05:30",
                "entry_price": 500.0,
                "exit_price": 510.0,
                "quantity": 10,
                "gross_pnl": 100.0,
                "charges": 20.0,
                "net_pnl": 80.0,
                "hard_sl": 490.0,
                "exit_reason": "SIGNAL_5M",
            },
            {
                "run_id": "test_run",
                "symbol": "SBIN",
                "direction": "SHORT",
                "timeframe_entry": "15m",
                "entry_time": "2024-01-15T12:00:00+05:30",
                "exit_time": "2024-01-15T13:00:00+05:30",
                "entry_price": 510.0,
                "exit_price": 500.0,
                "quantity": 10,
                "gross_pnl": 100.0,
                "charges": 20.0,
                "net_pnl": 80.0,
                "hard_sl": 520.0,
                "exit_reason": "HARD_SL",
            },
        ]

        summary = build_summary(trades, config)

        assert summary["total_trades"] == 2
        assert summary["winning_trades"] == 2
        assert summary["losing_trades"] == 0
        assert summary["win_rate_pct"] == 100.0
        assert summary["gross_pnl"] == 200.0
        assert summary["total_charges"] == 40.0
        assert summary["net_pnl"] == 160.0
        assert summary["avg_trade_pnl"] == 80.0
        assert summary["largest_win"] == 80.0
        assert summary["largest_loss"] == 80.0
        assert summary["final_capital"] == 100_160.0

    def test_summary_win_rate_correct(self, config: BacktestConfig) -> None:
        """Test that win rate is calculated correctly."""
        trades = [
            {
                "run_id": "test_run",
                "symbol": "SBIN",
                "direction": "LONG",
                "timeframe_entry": "5m",
                "entry_time": "2024-01-15T10:00:00+05:30",
                "exit_time": "2024-01-15T11:00:00+05:30",
                "entry_price": 500.0,
                "exit_price": 510.0,
                "quantity": 10,
                "gross_pnl": 100.0,
                "charges": 20.0,
                "net_pnl": 80.0,
                "hard_sl": 490.0,
                "exit_reason": "SIGNAL_5M",
            },
            {
                "run_id": "test_run",
                "symbol": "SBIN",
                "direction": "LONG",
                "timeframe_entry": "5m",
                "entry_time": "2024-01-15T12:00:00+05:30",
                "exit_time": "2024-01-15T13:00:00+05:30",
                "entry_price": 510.0,
                "exit_price": 490.0,
                "quantity": 10,
                "gross_pnl": -200.0,
                "charges": 20.0,
                "net_pnl": -220.0,
                "hard_sl": 500.0,
                "exit_reason": "HARD_SL",
            },
            {
                "run_id": "test_run",
                "symbol": "SBIN",
                "direction": "SHORT",
                "timeframe_entry": "15m",
                "entry_time": "2024-01-15T14:00:00+05:30",
                "exit_time": "2024-01-15T15:00:00+05:30",
                "entry_price": 500.0,
                "exit_price": 495.0,
                "quantity": 10,
                "gross_pnl": 50.0,
                "charges": 15.0,
                "net_pnl": 35.0,
                "hard_sl": 510.0,
                "exit_reason": "SIGNAL_15M",
            },
        ]

        summary = build_summary(trades, config)

        assert summary["total_trades"] == 3
        assert summary["winning_trades"] == 2
        assert summary["losing_trades"] == 1
        assert summary["win_rate_pct"] == pytest.approx(66.67, abs=0.01)

    def test_summary_max_drawdown_correct(self, config: BacktestConfig) -> None:
        """Test that max drawdown is calculated correctly."""
        trades = [
            {
                "run_id": "test_run",
                "symbol": "SBIN",
                "direction": "LONG",
                "timeframe_entry": "5m",
                "entry_time": "2024-01-15T10:00:00+05:30",
                "exit_time": "2024-01-15T11:00:00+05:30",
                "entry_price": 500.0,
                "exit_price": 510.0,
                "quantity": 10,
                "gross_pnl": 100.0,
                "charges": 20.0,
                "net_pnl": 80.0,
                "hard_sl": 490.0,
                "exit_reason": "SIGNAL_5M",
            },
            {
                "run_id": "test_run",
                "symbol": "SBIN",
                "direction": "LONG",
                "timeframe_entry": "5m",
                "entry_time": "2024-01-15T12:00:00+05:30",
                "exit_time": "2024-01-15T13:00:00+05:30",
                "entry_price": 510.0,
                "exit_price": 490.0,
                "quantity": 10,
                "gross_pnl": -200.0,
                "charges": 20.0,
                "net_pnl": -220.0,
                "hard_sl": 500.0,
                "exit_reason": "HARD_SL",
            },
            {
                "run_id": "test_run",
                "symbol": "SBIN",
                "direction": "SHORT",
                "timeframe_entry": "15m",
                "entry_time": "2024-01-15T14:00:00+05:30",
                "exit_time": "2024-01-15T15:00:00+05:30",
                "entry_price": 500.0,
                "exit_price": 495.0,
                "quantity": 10,
                "gross_pnl": 50.0,
                "charges": 15.0,
                "net_pnl": 35.0,
                "hard_sl": 510.0,
                "exit_reason": "SIGNAL_15M",
            },
        ]

        summary = build_summary(trades, config)

        # Cumulative PnL: 80, then 80-220=-140, then -140+35=-105
        # Peak at 80, drawdown from 80 to -140 is 220
        assert summary["max_drawdown"] == 220.0

    def test_summary_empty_trades_returns_zeros(self, config: BacktestConfig) -> None:
        """Test that empty trades list returns zero-filled summary."""
        summary = build_summary([], config)

        assert summary["total_trades"] == 0
        assert summary["winning_trades"] == 0
        assert summary["losing_trades"] == 0
        assert summary["win_rate_pct"] == 0.0
        assert summary["gross_pnl"] == 0.0
        assert summary["total_charges"] == 0.0
        assert summary["net_pnl"] == 0.0
        assert summary["max_drawdown"] == 0.0
        assert summary["avg_trade_pnl"] == 0.0
        assert summary["largest_win"] == 0.0
        assert summary["largest_loss"] == 0.0
        assert summary["final_capital"] == config.initial_capital

    def test_summary_final_capital_calculation(self, config: BacktestConfig) -> None:
        """Test that final capital is calculated correctly."""
        trades = [
            {
                "run_id": "test_run",
                "symbol": "SBIN",
                "direction": "LONG",
                "timeframe_entry": "5m",
                "entry_time": "2024-01-15T10:00:00+05:30",
                "exit_time": "2024-01-15T11:00:00+05:30",
                "entry_price": 500.0,
                "exit_price": 510.0,
                "quantity": 10,
                "gross_pnl": 100.0,
                "charges": 20.0,
                "net_pnl": 80.0,
                "hard_sl": 490.0,
                "exit_reason": "SIGNAL_5M",
            },
        ]

        summary = build_summary(trades, config)

        assert summary["initial_capital"] == 100_000.0
        assert summary["net_pnl"] == 80.0
        assert summary["final_capital"] == 100_080.0

    def test_summary_all_values_rounded_to_2_decimals(self, config: BacktestConfig) -> None:
        """Test that all monetary values are rounded to 2 decimals."""
        trades = [
            {
                "run_id": "test_run",
                "symbol": "SBIN",
                "direction": "LONG",
                "timeframe_entry": "5m",
                "entry_time": "2024-01-15T10:00:00+05:30",
                "exit_time": "2024-01-15T11:00:00+05:30",
                "entry_price": 500.123,
                "exit_price": 510.456,
                "quantity": 10,
                "gross_pnl": 100.333,
                "charges": 20.777,
                "net_pnl": 79.556,
                "hard_sl": 490.111,
                "exit_reason": "SIGNAL_5M",
            },
        ]

        summary = build_summary(trades, config)

        assert summary["gross_pnl"] == 100.33
        assert summary["total_charges"] == 20.78
        assert summary["net_pnl"] == 79.56
        assert summary["final_capital"] == 100_079.56
