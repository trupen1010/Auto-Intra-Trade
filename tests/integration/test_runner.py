"""Integration tests for the backtest runner."""

from __future__ import annotations

import sqlite3
import tempfile
from dataclasses import dataclass, field
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.db.repository import CandleRepository
from src.db.schema import create_all_tables
from src.engine.runner import run_backtest
from src.models.candle import Candle

IST = ZoneInfo("Asia/Kolkata")


@dataclass(slots=True)
class _ChargesCfg:
    """Test charges configuration."""

    brokerage_cap_per_order: float = 20.0
    brokerage_pct: float = 0.0003
    stt_sell_pct: float = 0.00025
    transaction_pct: float = 0.0000345
    gst_pct: float = 0.18
    sebi_pct: float = 0.000001
    stamp_duty_buy_pct: float = 0.00003


@dataclass(slots=True)
class _ConfigDict:
    """Test config dictionary builder."""

    initial_capital: float = 100_000.0
    risk_per_trade_pct: float = 0.01
    sl_atr_multiplier: float = 2.0
    entry_cutoff_time: time = time(15, 10)
    session_end_time: time = time(15, 30)
    atr_period: int = 3
    atr_sensitivity: int = 2
    charges: _ChargesCfg = field(default_factory=_ChargesCfg)

    def to_dict(self) -> dict:
        """Convert to dictionary for BacktestConfig."""
        return {
            "initial_capital": self.initial_capital,
            "risk_per_trade_pct": self.risk_per_trade_pct,
            "sl_atr_multiplier": self.sl_atr_multiplier,
            "atr_period": self.atr_period,
            "atr_sensitivity": self.atr_sensitivity,
            "entry_cutoff_time": self.entry_cutoff_time,
            "session_end_time": self.session_end_time,
            "charges": {
                "brokerage_cap_per_order": self.charges.brokerage_cap_per_order,
                "brokerage_pct": self.charges.brokerage_pct,
                "stt_sell_pct": self.charges.stt_sell_pct,
                "transaction_pct": self.charges.transaction_pct,
                "gst_pct": self.charges.gst_pct,
                "sebi_pct": self.charges.sebi_pct,
                "stamp_duty_buy_pct": self.charges.stamp_duty_buy_pct,
            },
        }


def _dt(year: int, month: int, day: int, hour: int, minute: int) -> datetime:
    """Create an IST-aware datetime."""
    return datetime(year, month, day, hour, minute, tzinfo=IST)


def _candle(
    ts: datetime, o: float, h: float, l: float, c: float, timeframe: str = "5m"
) -> Candle:
    """Create a test candle."""
    return Candle(
        symbol="TESTSTOCK",
        timeframe=timeframe,
        timestamp=ts,
        open=o,
        high=h,
        low=l,
        close=c,
        volume=1000.0,
    )


def test_run_backtest_with_valid_config() -> None:
    """Test that run_backtest executes successfully with valid config."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        conn = sqlite3.connect(db_path)
        create_all_tables(conn)

        # Create 3-day synthetic data.
        candles_1d = [
            _candle(_dt(2024, 1, 1, 0, 0), 100, 110, 95, 105, "1d"),
            _candle(_dt(2024, 1, 2, 0, 0), 105, 115, 100, 110, "1d"),
            _candle(_dt(2024, 1, 3, 0, 0), 110, 120, 105, 115, "1d"),
        ]

        candles_15m = []
        for day_offset in range(3):
            ts = _dt(2024, 1, 1, 9, 15) + timedelta(days=day_offset)
            end_time = _dt(2024, 1, 1, 15, 30) + timedelta(days=day_offset)
            while ts <= end_time:
                candles_15m.append(
                    _candle(ts, 100 + day_offset * 5, 110, 95, 105, "15m")
                )
                ts += timedelta(minutes=15)

        candles_5m = []
        for day_offset in range(3):
            ts = _dt(2024, 1, 1, 9, 15) + timedelta(days=day_offset)
            end_time = _dt(2024, 1, 1, 15, 30) + timedelta(days=day_offset)
            while ts <= end_time:
                candles_5m.append(_candle(ts, 100 + day_offset * 5, 110, 95, 105, "5m"))
                ts += timedelta(minutes=5)

        CandleRepository.insert_candles(conn, candles_1d)
        CandleRepository.insert_candles(conn, candles_15m)
        CandleRepository.insert_candles(conn, candles_5m)
        conn.close()

        # Run backtest using runner.
        config_dict = _ConfigDict().to_dict()
        result, output_dir = run_backtest(
            symbol="TESTSTOCK",
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 3),
            config_dict=config_dict,
            db_path=db_path,
        )

        assert result is not None
        assert isinstance(result.trades, list)
        assert isinstance(result.rejected_trades, list)
        assert isinstance(output_dir, str)
        assert "TESTSTOCK" not in output_dir  # run_id is UUID, not symbol

    finally:
        import os

        if os.path.exists(db_path):
            os.remove(db_path)


def test_run_backtest_invalid_config_raises_error() -> None:
    """Test that run_backtest raises ValueError on invalid config."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        # Missing required keys in config.
        config_dict = {"initial_capital": 100_000.0}

        from src.models.backtest_config import BacktestConfig

        with pytest.raises(ValueError, match="Missing required config keys"):
            BacktestConfig.from_dict(config_dict, run_id="test", symbol="TESTSTOCK")

    finally:
        import os

        if os.path.exists(db_path):
            os.remove(db_path)


def test_run_backtest_closes_connection_on_error() -> None:
    """Test that database connection is closed even on error."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        conn = sqlite3.connect(db_path)
        create_all_tables(conn)
        # Don't insert any candles — will cause backtest to fail.
        conn.close()

        config_dict = _ConfigDict().to_dict()

        from src.utils.exceptions import ExecutionError

        with pytest.raises(ExecutionError):
            run_backtest(
                symbol="TESTSTOCK",
                start_date=date(2024, 1, 1),
                end_date=date(2024, 1, 3),
                config_dict=config_dict,
                db_path=db_path,
            )

        # Verify connection is closed by checking we can delete the file.
        import os

        os.remove(db_path)
        assert not os.path.exists(db_path)

    except FileNotFoundError:
        # File already deleted in cleanup — that's fine.
        pass
