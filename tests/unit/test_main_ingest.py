"""Unit tests for ingest CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.main import main


class TestIngestCommand:
    """Tests for 'ingest' CLI command."""

    def test_ingest_command_success(self, tmp_path: Path) -> None:
        """Test successful ingest command execution."""
        token_file = tmp_path / "token.json"
        token_file.write_text('{"access_token": "test_token", "expires_at": "2099-01-01T00:00:00+05:30"}')
        db_file = tmp_path / "test.db"

        with patch("src.main.ingest_symbol", return_value={"1d": 10, "15m": 20, "5m": 30}):
            exit_code = main(
                [
                    "ingest",
                    "--symbol",
                    "NIFTY",
                    "--instrument-key",
                    "NSE_INDEX|Nifty 50",
                    "--start-date",
                    "2024-01-01",
                    "--end-date",
                    "2024-01-31",
                    "--db",
                    str(db_file),
                    "--token-file",
                    str(token_file),
                ]
            )

        assert exit_code == 0

    def test_ingest_command_missing_token_exits_with_error(self, tmp_path: Path) -> None:
        """Test that missing token exits with error code 1."""
        token_file = tmp_path / "nonexistent.json"
        db_file = tmp_path / "test.db"

        exit_code = main(
            [
                "ingest",
                "--symbol",
                "NIFTY",
                "--instrument-key",
                "NSE_INDEX|Nifty 50",
                "--start-date",
                "2024-01-01",
                "--end-date",
                "2024-01-31",
                "--db",
                str(db_file),
                "--token-file",
                str(token_file),
            ]
        )

        assert exit_code == 1

    def test_ingest_command_invalid_date_exits_with_error(self, tmp_path: Path) -> None:
        """Test that invalid date format exits with error code 1."""
        token_file = tmp_path / "token.json"
        token_file.write_text('{"access_token": "test_token", "expires_at": "2099-01-01T00:00:00+05:30"}')
        db_file = tmp_path / "test.db"

        exit_code = main(
            [
                "ingest",
                "--symbol",
                "NIFTY",
                "--instrument-key",
                "NSE_INDEX|Nifty 50",
                "--start-date",
                "01-01-2024",  # Invalid format
                "--end-date",
                "2024-01-31",
                "--db",
                str(db_file),
                "--token-file",
                str(token_file),
            ]
        )

        assert exit_code == 1

    def test_ingest_command_missing_required_arg_exits_with_error(self) -> None:
        """Test that missing required argument exits with error."""
        try:
            exit_code = main(
                [
                    "ingest",
                    "--symbol",
                    "NIFTY",
                    # Missing --instrument-key, --start-date, --end-date, --db
                ]
            )
            assert exit_code != 0
        except SystemExit as e:
            assert e.code != 0

    def test_ingest_command_calls_ingest_symbol(self, tmp_path: Path) -> None:
        """Test that ingest command calls ingest_symbol."""
        token_file = tmp_path / "token.json"
        token_file.write_text('{"access_token": "test_token", "expires_at": "2099-01-01T00:00:00+05:30"}')
        db_file = tmp_path / "test.db"

        with patch("src.main.ingest_symbol", return_value={"1d": 10, "15m": 20, "5m": 30}) as mock_ingest:
            main(
                [
                    "ingest",
                    "--symbol",
                    "NIFTY",
                    "--instrument-key",
                    "NSE_INDEX|Nifty 50",
                    "--start-date",
                    "2024-01-01",
                    "--end-date",
                    "2024-01-31",
                    "--db",
                    str(db_file),
                    "--token-file",
                    str(token_file),
                ]
            )

        mock_ingest.assert_called_once()

    def test_ingest_command_with_verbose_flag(self, tmp_path: Path) -> None:
        """Test that --verbose flag enables INFO logging."""
        token_file = tmp_path / "token.json"
        token_file.write_text('{"access_token": "test_token", "expires_at": "2099-01-01T00:00:00+05:30"}')
        db_file = tmp_path / "test.db"

        with patch("src.main.ingest_symbol", return_value={"1d": 10, "15m": 20, "5m": 30}):
            with patch("src.main._setup_logging") as mock_setup:
                main(
                    [
                        "ingest",
                        "--symbol",
                        "NIFTY",
                        "--instrument-key",
                        "NSE_INDEX|Nifty 50",
                        "--start-date",
                        "2024-01-01",
                        "--end-date",
                        "2024-01-31",
                        "--db",
                        str(db_file),
                        "--token-file",
                        str(token_file),
                        "--verbose",
                    ]
                )

                mock_setup.assert_called_once_with(True, False)
