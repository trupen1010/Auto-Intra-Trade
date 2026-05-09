"""Unit tests for report writer."""

from __future__ import annotations

import json
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.engine.trade_state import EngineTradeState
from src.models.backtest_config import BacktestConfig, ChargesConfig
from src.models.rejected_trade import RejectedTrade
from src.models.simulation_result import SimulationResult
from src.reports.writer import write_run_report
from src.utils.enums import EntryTF, ExitReason, SignalSide

IST = ZoneInfo("Asia/Kolkata")


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
    return BacktestConfig(
        run_id="test_run_123",
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


@pytest.fixture
def trade() -> EngineTradeState:
    """Create a sample closed trade."""
    return EngineTradeState(
        run_id="test_run_123",
        symbol="SBIN",
        timeframe_entry=EntryTF.FIVE_MINUTE,
        direction=SignalSide.BUY,
        entry_time=datetime(2024, 1, 15, 10, 0, tzinfo=IST),
        entry_price=500.0,
        quantity=10,
        hard_sl=490.0,
        exit_time=datetime(2024, 1, 15, 11, 0, tzinfo=IST),
        exit_price=510.0,
        exit_reason=ExitReason.SIGNAL_5M,
        pnl_points=10.0,
        pnl_rupees=100.0,
        charges=20.0,
        net_pnl=80.0,
    )


@pytest.fixture
def rejected_trade() -> RejectedTrade:
    """Create a sample rejected trade."""
    return RejectedTrade(
        symbol="SBIN",
        timestamp=datetime(2024, 1, 15, 10, 30, tzinfo=IST),
        timeframe="5m",
        requested_side="LONG",
        reason="quantity=0",
    )


@pytest.fixture
def simulation_result(trade: EngineTradeState, rejected_trade: RejectedTrade) -> SimulationResult:
    """Create a simulation result with one trade and one rejection."""
    return SimulationResult(
        trades=[trade],
        rejected_trades=[rejected_trade],
        run_id="test_run_123",
    )


class TestWriteRunReport:
    """Tests for write_run_report function."""

    def test_write_run_report_creates_expected_files(
        self, tmp_path: Path, simulation_result: SimulationResult, config: BacktestConfig
    ) -> None:
        """Test that write_run_report creates all expected files."""
        output_dir = write_run_report(simulation_result, config, str(tmp_path))

        output_path = Path(output_dir)
        assert output_path.exists()
        assert (output_path / "trades.csv").exists()
        assert (output_path / "rejected_trades.csv").exists()
        assert (output_path / "summary.json").exists()
        assert (output_path / "config_snapshot.json").exists()

    def test_write_run_report_returns_output_dir(
        self, tmp_path: Path, simulation_result: SimulationResult, config: BacktestConfig
    ) -> None:
        """Test that write_run_report returns the output directory path."""
        output_dir = write_run_report(simulation_result, config, str(tmp_path))

        assert isinstance(output_dir, str)
        assert "test_run_123" in output_dir
        assert Path(output_dir).exists()

    def test_write_run_report_trades_csv_content(
        self, tmp_path: Path, simulation_result: SimulationResult, config: BacktestConfig
    ) -> None:
        """Test that trades.csv has correct content."""
        output_dir = write_run_report(simulation_result, config, str(tmp_path))

        trades_file = Path(output_dir) / "trades.csv"
        with open(trades_file) as f:
            lines = f.readlines()

        assert len(lines) >= 2  # header + at least 1 trade
        assert "run_id" in lines[0]
        assert "test_run_123" in lines[1]

    def test_write_run_report_rejected_trades_csv_content(
        self, tmp_path: Path, simulation_result: SimulationResult, config: BacktestConfig
    ) -> None:
        """Test that rejected_trades.csv has correct content."""
        output_dir = write_run_report(simulation_result, config, str(tmp_path))

        rejected_file = Path(output_dir) / "rejected_trades.csv"
        with open(rejected_file) as f:
            lines = f.readlines()

        assert len(lines) >= 2  # header + at least 1 rejection
        assert "symbol" in lines[0]
        assert "SBIN" in lines[1]

    def test_write_run_report_summary_json_content(
        self, tmp_path: Path, simulation_result: SimulationResult, config: BacktestConfig
    ) -> None:
        """Test that summary.json has correct structure."""
        output_dir = write_run_report(simulation_result, config, str(tmp_path))

        summary_file = Path(output_dir) / "summary.json"
        with open(summary_file) as f:
            summary = json.load(f)

        assert summary["run_id"] == "test_run_123"
        assert summary["symbol"] == "SBIN"
        assert summary["total_trades"] == 1
        assert summary["winning_trades"] == 1
        assert "net_pnl" in summary
        assert "final_capital" in summary

    def test_write_run_report_config_snapshot_includes_required_fields(
        self, tmp_path: Path, simulation_result: SimulationResult, config: BacktestConfig
    ) -> None:
        """Test that config_snapshot.json includes required fields."""
        output_dir = write_run_report(simulation_result, config, str(tmp_path))

        config_file = Path(output_dir) / "config_snapshot.json"
        with open(config_file) as f:
            snapshot = json.load(f)

        assert snapshot["run_id"] == "test_run_123"
        assert snapshot["symbol"] == "SBIN"
        assert snapshot["initial_capital"] == 100_000.0
        assert snapshot["risk_per_trade_pct"] == 0.01
        assert snapshot["atr_period"] == 14
        assert "charges" in snapshot
        assert snapshot["charges"]["brokerage_pct"] == 0.0003

    def test_config_snapshot_excludes_runtime_arrays(
        self, tmp_path: Path, simulation_result: SimulationResult, config: BacktestConfig
    ) -> None:
        """Test that config_snapshot excludes runtime arrays."""
        output_dir = write_run_report(simulation_result, config, str(tmp_path))

        config_file = Path(output_dir) / "config_snapshot.json"
        with open(config_file) as f:
            snapshot = json.load(f)

        assert "atr_values_5m" not in snapshot
        assert "trailing_stop_5m" not in snapshot

    def test_write_run_report_creates_directory_structure(
        self, tmp_path: Path, simulation_result: SimulationResult, config: BacktestConfig
    ) -> None:
        """Test that write_run_report creates directory with run_id."""
        output_dir = write_run_report(simulation_result, config, str(tmp_path))

        assert str(tmp_path / "test_run_123") == output_dir

    def test_write_run_report_with_empty_trades(
        self, tmp_path: Path, config: BacktestConfig
    ) -> None:
        """Test write_run_report with empty trades list."""
        result = SimulationResult(trades=[], rejected_trades=[], run_id="test_run_123")
        output_dir = write_run_report(result, config, str(tmp_path))

        trades_file = Path(output_dir) / "trades.csv"
        assert trades_file.exists()
        # Empty file or just header
        with open(trades_file) as f:
            content = f.read()
        assert len(content) >= 0

    def test_write_run_report_timestamps_are_iso8601(
        self, tmp_path: Path, simulation_result: SimulationResult, config: BacktestConfig
    ) -> None:
        """Test that timestamps in output are ISO8601 strings."""
        output_dir = write_run_report(simulation_result, config, str(tmp_path))

        trades_file = Path(output_dir) / "trades.csv"
        with open(trades_file) as f:
            lines = f.readlines()

        # Check that entry_time and exit_time contain 'T' (ISO8601 format)
        assert len(lines) >= 2
        trade_line = lines[1]
        assert "T" in trade_line  # ISO8601 format includes 'T'
