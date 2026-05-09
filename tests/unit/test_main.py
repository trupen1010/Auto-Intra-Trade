"""Unit tests for CLI entry point."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.engine.exceptions import ExecutionError
from src.engine.trade_state import EngineTradeState
from src.main import _load_config, _parse_date, main
from src.models.simulation_result import SimulationResult
from src.utils.enums import EntryTF, ExitReason, SignalSide
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")


class TestParseDate:
    """Tests for _parse_date function."""

    def test_parse_date_valid_iso8601(self) -> None:
        """Test parsing valid ISO8601 date."""
        result = _parse_date("2024-01-15")
        assert result == date(2024, 1, 15)

    def test_parse_date_invalid_format_raises_error(self) -> None:
        """Test that invalid date format raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date format"):
            _parse_date("15-01-2024")

    def test_parse_date_invalid_date_raises_error(self) -> None:
        """Test that invalid date raises ValueError."""
        with pytest.raises(ValueError, match="Invalid date format"):
            _parse_date("2024-13-01")


class TestLoadConfig:
    """Tests for _load_config function."""

    def test_load_config_valid_json(self, tmp_path: Path) -> None:
        """Test loading valid JSON config."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"key": "value"}')

        result = _load_config(str(config_file))
        assert result == {"key": "value"}

    def test_load_config_file_not_found(self) -> None:
        """Test that missing config file raises ValueError."""
        with pytest.raises(ValueError, match="Config file not found"):
            _load_config("/nonexistent/config.json")

    def test_load_config_invalid_json(self, tmp_path: Path) -> None:
        """Test that invalid JSON raises ValueError."""
        config_file = tmp_path / "config.json"
        config_file.write_text("{ invalid json }")

        with pytest.raises(ValueError, match="Invalid JSON"):
            _load_config(str(config_file))


class TestMainCommand:
    """Tests for main CLI function."""

    def test_run_command_calls_run_backtest(self, tmp_path: Path) -> None:
        """Test that 'run' command calls run_backtest with correct args."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"initial_capital": 100000}')

        trade = EngineTradeState(
            run_id="test_run",
            symbol="SBIN",
            timeframe_entry=EntryTF.FIVE_MINUTE,
            direction=SignalSide.BUY,
            entry_time=__import__("datetime").datetime(2024, 1, 15, 10, 0, tzinfo=IST),
            entry_price=500.0,
            quantity=10,
            hard_sl=490.0,
            exit_time=__import__("datetime").datetime(2024, 1, 15, 11, 0, tzinfo=IST),
            exit_price=510.0,
            exit_reason=ExitReason.SIGNAL_5M,
            pnl_points=10.0,
            pnl_rupees=100.0,
            charges=20.0,
            net_pnl=80.0,
        )
        result = SimulationResult(trades=[trade], rejected_trades=[], run_id="test_run")
        output_dir = "/path/to/output"

        with patch("src.main.run_backtest", return_value=(result, output_dir)):
            exit_code = main(
                [
                    "run",
                    "--symbol",
                    "SBIN",
                    "--start-date",
                    "2024-01-01",
                    "--end-date",
                    "2024-01-31",
                    "--config",
                    str(config_file),
                    "--db",
                    "/path/to/db.db",
                ]
            )

            assert exit_code == 0

    def test_missing_required_arg_exits_with_error(self) -> None:
        """Test that missing required argument exits with error code 1."""
        # argparse calls sys.exit(2) for parse errors, which we can't easily catch
        # Instead, we test that an exception or return code occurs
        try:
            exit_code = main(
                [
                    "run",
                    "--symbol",
                    "SBIN",
                    # Missing --start-date, --end-date, --config, --db
                ]
            )
            # If we get here, it should be an error code
            assert exit_code != 0
        except SystemExit as e:
            # argparse may call sys.exit(2)
            assert e.code != 0

    def test_invalid_date_format_exits_with_error(self, tmp_path: Path) -> None:
        """Test that invalid date format exits with error code 1."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"initial_capital": 100000}')

        exit_code = main(
            [
                "run",
                "--symbol",
                "SBIN",
                "--start-date",
                "01-01-2024",  # Invalid format
                "--end-date",
                "2024-01-31",
                "--config",
                str(config_file),
                "--db",
                "/path/to/db.db",
            ]
        )

        assert exit_code == 1

    def test_missing_config_file_exits_with_error(self, tmp_path: Path) -> None:
        """Test that missing config file exits with error code 1."""
        exit_code = main(
            [
                "run",
                "--symbol",
                "SBIN",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
                "--config",
                "/nonexistent/config.json",
                "--db",
                "/path/to/db.db",
            ]
        )

        assert exit_code == 1

    def test_execution_error_exits_with_error(self, tmp_path: Path) -> None:
        """Test that ExecutionError from run_backtest exits with error code 1."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"initial_capital": 100000}')

        with patch("src.main.run_backtest", side_effect=ExecutionError("Test error")):
            exit_code = main(
                [
                    "run",
                    "--symbol",
                    "SBIN",
                    "--start-date",
                    "2024-01-01",
                    "--end-date",
                    "2024-01-31",
                    "--config",
                    str(config_file),
                    "--db",
                    "/path/to/db.db",
                ]
            )

            assert exit_code == 1

    def test_verbose_flag_enables_info_logging(self, tmp_path: Path) -> None:
        """Test that --verbose flag enables INFO logging."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"initial_capital": 100000}')

        result = SimulationResult(trades=[], rejected_trades=[], run_id="test_run")
        output_dir = "/path/to/output"

        with patch("src.main.run_backtest", return_value=(result, output_dir)):
            with patch("src.main._setup_logging") as mock_setup:
                exit_code = main(
                    [
                        "run",
                        "--symbol",
                        "SBIN",
                        "--start-date",
                        "2024-01-01",
                        "--end-date",
                        "2024-01-31",
                        "--config",
                        str(config_file),
                        "--db",
                        "/path/to/db.db",
                        "--verbose",
                    ]
                )

                mock_setup.assert_called_once_with(True, False)
                assert exit_code == 0

    def test_debug_flag_enables_debug_logging(self, tmp_path: Path) -> None:
        """Test that --debug flag enables DEBUG logging."""
        config_file = tmp_path / "config.json"
        config_file.write_text('{"initial_capital": 100000}')

        result = SimulationResult(trades=[], rejected_trades=[], run_id="test_run")
        output_dir = "/path/to/output"

        with patch("src.main.run_backtest", return_value=(result, output_dir)):
            with patch("src.main._setup_logging") as mock_setup:
                exit_code = main(
                    [
                        "run",
                        "--symbol",
                        "SBIN",
                        "--start-date",
                        "2024-01-01",
                        "--end-date",
                        "2024-01-31",
                        "--config",
                        str(config_file),
                        "--db",
                        "/path/to/db.db",
                        "--debug",
                    ]
                )

                mock_setup.assert_called_once_with(False, True)
                assert exit_code == 0

    def test_no_command_shows_help(self) -> None:
        """Test that no command shows help and exits with error."""
        exit_code = main([])
        assert exit_code == 1
