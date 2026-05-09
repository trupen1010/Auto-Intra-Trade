"""Unit tests for backtest configuration models."""

from __future__ import annotations

from datetime import date, time

import pytest

from src.models.backtest_config import BacktestConfig, ChargesConfig


@pytest.fixture
def valid_charges_dict() -> dict:
    """Standard charges configuration."""
    return {
        "brokerage_pct": 0.0003,
        "brokerage_cap_per_order": 20.0,
        "stt_sell_pct": 0.00025,
        "transaction_pct": 0.0000345,
        "sebi_pct": 0.000001,
        "gst_pct": 0.18,
        "stamp_duty_buy_pct": 0.00003,
    }


@pytest.fixture
def valid_config_dict(valid_charges_dict: dict) -> dict:
    """Standard backtest configuration."""
    return {
        "initial_capital": 100_000.0,
        "risk_per_trade_pct": 0.01,
        "sl_atr_multiplier": 2.0,
        "atr_period": 14,
        "atr_sensitivity": 1,
        "start_date": date(2024, 1, 1),
        "end_date": date(2024, 1, 31),
        "entry_cutoff_time": time(15, 0),
        "session_end_time": time(15, 15),
        "charges": valid_charges_dict,
    }


class TestChargesConfig:
    """Tests for ChargesConfig dataclass."""

    def test_charges_config_valid_construction(self, valid_charges_dict: dict) -> None:
        """Test valid ChargesConfig creation."""
        charges = ChargesConfig(**valid_charges_dict)
        assert charges.brokerage_pct == 0.0003
        assert charges.brokerage_cap_per_order == 20.0
        assert charges.gst_pct == 0.18

    def test_charges_config_negative_value_raises_error(self) -> None:
        """Test that negative charge values raise ValueError."""
        charges_dict = {
            "brokerage_pct": -0.0003,
            "brokerage_cap_per_order": 20.0,
            "stt_sell_pct": 0.00025,
            "transaction_pct": 0.0000345,
            "sebi_pct": 0.000001,
            "gst_pct": 0.18,
            "stamp_duty_buy_pct": 0.00003,
        }
        with pytest.raises(ValueError, match="non-negative"):
            ChargesConfig(**charges_dict)

    def test_charges_config_zero_values_allowed(self) -> None:
        """Test that zero charge values are valid."""
        charges = ChargesConfig(
            brokerage_pct=0.0,
            brokerage_cap_per_order=0.0,
            stt_sell_pct=0.0,
            transaction_pct=0.0,
            sebi_pct=0.0,
            gst_pct=0.0,
            stamp_duty_buy_pct=0.0,
        )
        assert charges.brokerage_pct == 0.0


class TestBacktestConfig:
    """Tests for BacktestConfig dataclass."""

    def test_backtest_config_valid_construction(self, valid_config_dict: dict) -> None:
        """Test valid BacktestConfig creation."""
        config = BacktestConfig.from_dict(
            valid_config_dict, run_id="test_123", symbol="SBIN"
        )
        assert config.run_id == "test_123"
        assert config.symbol == "SBIN"
        assert config.initial_capital == 100_000.0
        assert config.risk_per_trade_pct == 0.01

    def test_backtest_config_invalid_capital_raises_error(self) -> None:
        """Test that non-positive capital raises ValueError."""
        config_dict = {
            "initial_capital": 0,
            "risk_per_trade_pct": 0.01,
            "sl_atr_multiplier": 2.0,
            "atr_period": 14,
            "atr_sensitivity": 1,
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
            "entry_cutoff_time": time(15, 0),
            "session_end_time": time(15, 15),
            "charges": {
                "brokerage_pct": 0.0003,
                "brokerage_cap_per_order": 20.0,
                "stt_sell_pct": 0.00025,
                "transaction_pct": 0.0000345,
                "sebi_pct": 0.000001,
                "gst_pct": 0.18,
                "stamp_duty_buy_pct": 0.00003,
            },
        }
        with pytest.raises(ValueError, match="initial_capital must be positive"):
            BacktestConfig.from_dict(config_dict, run_id="test_123", symbol="SBIN")

    def test_backtest_config_invalid_risk_pct_below_zero(self) -> None:
        """Test that risk_pct <= 0 raises ValueError."""
        config_dict = {
            "initial_capital": 100_000.0,
            "risk_per_trade_pct": 0,
            "sl_atr_multiplier": 2.0,
            "atr_period": 14,
            "atr_sensitivity": 1,
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
            "entry_cutoff_time": time(15, 0),
            "session_end_time": time(15, 15),
            "charges": {
                "brokerage_pct": 0.0003,
                "brokerage_cap_per_order": 20.0,
                "stt_sell_pct": 0.00025,
                "transaction_pct": 0.0000345,
                "sebi_pct": 0.000001,
                "gst_pct": 0.18,
                "stamp_duty_buy_pct": 0.00003,
            },
        }
        with pytest.raises(ValueError, match="risk_per_trade_pct must be in"):
            BacktestConfig.from_dict(config_dict, run_id="test_123", symbol="SBIN")

    def test_backtest_config_invalid_risk_pct_above_one(self) -> None:
        """Test that risk_pct >= 1 raises ValueError."""
        config_dict = {
            "initial_capital": 100_000.0,
            "risk_per_trade_pct": 1.0,
            "sl_atr_multiplier": 2.0,
            "atr_period": 14,
            "atr_sensitivity": 1,
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
            "entry_cutoff_time": time(15, 0),
            "session_end_time": time(15, 15),
            "charges": {
                "brokerage_pct": 0.0003,
                "brokerage_cap_per_order": 20.0,
                "stt_sell_pct": 0.00025,
                "transaction_pct": 0.0000345,
                "sebi_pct": 0.000001,
                "gst_pct": 0.18,
                "stamp_duty_buy_pct": 0.00003,
            },
        }
        with pytest.raises(ValueError, match="risk_per_trade_pct must be in"):
            BacktestConfig.from_dict(config_dict, run_id="test_123", symbol="SBIN")

    def test_backtest_config_invalid_dates_raises_error(self) -> None:
        """Test that start_date >= end_date raises ValueError."""
        config_dict = {
            "initial_capital": 100_000.0,
            "risk_per_trade_pct": 0.01,
            "sl_atr_multiplier": 2.0,
            "atr_period": 14,
            "atr_sensitivity": 1,
            "start_date": date(2024, 1, 31),
            "end_date": date(2024, 1, 1),
            "entry_cutoff_time": time(15, 0),
            "session_end_time": time(15, 15),
            "charges": {
                "brokerage_pct": 0.0003,
                "brokerage_cap_per_order": 20.0,
                "stt_sell_pct": 0.00025,
                "transaction_pct": 0.0000345,
                "sebi_pct": 0.000001,
                "gst_pct": 0.18,
                "stamp_duty_buy_pct": 0.00003,
            },
        }
        with pytest.raises(ValueError, match="start_date must be before end_date"):
            BacktestConfig.from_dict(config_dict, run_id="test_123", symbol="SBIN")

    def test_backtest_config_invalid_cutoff_time_raises_error(self) -> None:
        """Test that entry_cutoff_time >= session_end_time raises ValueError."""
        config_dict = {
            "initial_capital": 100_000.0,
            "risk_per_trade_pct": 0.01,
            "sl_atr_multiplier": 2.0,
            "atr_period": 14,
            "atr_sensitivity": 1,
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
            "entry_cutoff_time": time(15, 20),
            "session_end_time": time(15, 15),
            "charges": {
                "brokerage_pct": 0.0003,
                "brokerage_cap_per_order": 20.0,
                "stt_sell_pct": 0.00025,
                "transaction_pct": 0.0000345,
                "sebi_pct": 0.000001,
                "gst_pct": 0.18,
                "stamp_duty_buy_pct": 0.00003,
            },
        }
        with pytest.raises(ValueError, match="entry_cutoff_time must be before"):
            BacktestConfig.from_dict(config_dict, run_id="test_123", symbol="SBIN")

    def test_from_dict_missing_required_key(self) -> None:
        """Test that missing required keys raise ValueError."""
        config_dict = {
            "initial_capital": 100_000.0,
            # missing risk_per_trade_pct and others
        }
        with pytest.raises(ValueError, match="Missing required config keys"):
            BacktestConfig.from_dict(config_dict, run_id="test_123", symbol="SBIN")

    def test_from_dict_invalid_charges_type(self) -> None:
        """Test that non-dict charges raises TypeError."""
        config_dict = {
            "initial_capital": 100_000.0,
            "risk_per_trade_pct": 0.01,
            "sl_atr_multiplier": 2.0,
            "atr_period": 14,
            "atr_sensitivity": 1,
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
            "entry_cutoff_time": time(15, 0),
            "session_end_time": time(15, 15),
            "charges": "invalid",
        }
        with pytest.raises(TypeError, match="charges must be a dictionary"):
            BacktestConfig.from_dict(config_dict, run_id="test_123", symbol="SBIN")

    def test_backtest_config_mutable_computed_fields(
        self, valid_config_dict: dict
    ) -> None:
        """Test that computed fields can be updated after creation."""
        config = BacktestConfig.from_dict(
            valid_config_dict, run_id="test_123", symbol="SBIN"
        )
        assert config.atr_values_5m == []
        config.atr_values_5m = [1.0, 2.0, 3.0]
        assert config.atr_values_5m == [1.0, 2.0, 3.0]

    def test_backtest_config_runtime_arrays_initialized_empty(
        self, valid_config_dict: dict
    ) -> None:
        """Test that runtime arrays are initialized as empty lists."""
        config = BacktestConfig.from_dict(
            valid_config_dict, run_id="test_123", symbol="SBIN"
        )
        assert config.atr_values_5m == []
        assert config.trailing_stop_5m == []

    def test_from_dict_parses_time_strings(self, valid_charges_dict: dict) -> None:
        """Test that time strings (HH:MM) are parsed to datetime.time objects."""
        config_dict = {
            "initial_capital": 100_000.0,
            "risk_per_trade_pct": 0.01,
            "sl_atr_multiplier": 2.0,
            "atr_period": 14,
            "atr_sensitivity": 1,
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
            "entry_cutoff_time": "15:00",  # String format
            "session_end_time": "15:15",  # String format
            "charges": valid_charges_dict,
        }
        config = BacktestConfig.from_dict(config_dict, run_id="test_123", symbol="SBIN")
        assert config.entry_cutoff_time == time(15, 0)
        assert config.session_end_time == time(15, 15)

    def test_from_dict_accepts_time_objects(self, valid_charges_dict: dict) -> None:
        """Test that already-parsed time objects are accepted."""
        config_dict = {
            "initial_capital": 100_000.0,
            "risk_per_trade_pct": 0.01,
            "sl_atr_multiplier": 2.0,
            "atr_period": 14,
            "atr_sensitivity": 1,
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
            "entry_cutoff_time": time(15, 0),  # Already a time object
            "session_end_time": time(15, 15),  # Already a time object
            "charges": valid_charges_dict,
        }
        config = BacktestConfig.from_dict(config_dict, run_id="test_123", symbol="SBIN")
        assert config.entry_cutoff_time == time(15, 0)
        assert config.session_end_time == time(15, 15)

    def test_from_dict_invalid_time_format_raises_error(
        self, valid_charges_dict: dict
    ) -> None:
        """Test that invalid time format raises ValueError."""
        config_dict = {
            "initial_capital": 100_000.0,
            "risk_per_trade_pct": 0.01,
            "sl_atr_multiplier": 2.0,
            "atr_period": 14,
            "atr_sensitivity": 1,
            "start_date": date(2024, 1, 1),
            "end_date": date(2024, 1, 31),
            "entry_cutoff_time": "invalid_time",
            "session_end_time": "15:15",
            "charges": valid_charges_dict,
        }
        with pytest.raises(ValueError, match="Invalid time format"):
            BacktestConfig.from_dict(config_dict, run_id="test_123", symbol="SBIN")
