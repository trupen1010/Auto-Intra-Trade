"""Unit tests for configuration loading."""

from __future__ import annotations

from datetime import time
from pathlib import Path

import pytest

from src.config import load_config
from src.models.config_models import AppConfig
from src.utils.exceptions import ConfigValidationError


def test_load_config_returns_valid_appconfig() -> None:
    """Loading the default settings file returns a valid AppConfig."""
    config = load_config("config/settings.yaml")

    assert isinstance(config, AppConfig)
    assert config.execution.entry_cutoff_time == time(hour=14, minute=30)
    assert config.execution.forced_exit_time == time(hour=15, minute=15)


def test_load_config_raises_on_missing_file() -> None:
    """Loading a missing file raises ConfigValidationError."""
    with pytest.raises(ConfigValidationError):
        load_config("config/missing.yaml")


def test_load_config_raises_on_invalid_yaml(tmp_path: Path) -> None:
    """Invalid YAML content raises ConfigValidationError."""
    config_path = tmp_path / "bad.yaml"
    config_path.write_text("charges: [broken\n", encoding="utf-8")

    with pytest.raises(ConfigValidationError):
        load_config(config_path)


def test_load_config_raises_on_invalid_values(tmp_path: Path) -> None:
    """Invalid values rejected by Pydantic raise ConfigValidationError."""
    config_path = tmp_path / "invalid_values.yaml"
    config_path.write_text(
        """
charges:
  brokerage_pct: -0.0003
  brokerage_cap_per_order: 20.0
  stt_sell_pct: 0.001
  transaction_pct: 0.0000335
  gst_pct: 0.18
  sebi_pct: 0.000001
  stamp_duty_buy_pct: 0.00003
strategy:
  atr_period: 1
  sensitivity: 1
  hard_sl_atr_multiplier: 1.5
  risk_per_trade_pct: 1.0
  allow_short: false
  warmup_bars_5m: 50
  warmup_bars_15m: 20
  warmup_bars_1d: 10
execution:
  entry_model: next_open
  exit_model: next_open
  slippage_pct: 0.0002
  entry_cutoff_time: "14:30"
  forced_exit_time: "15:15"
  one_trade_at_a_time: true
  same_candle_reentry_block: true
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigValidationError):
        load_config(config_path)
