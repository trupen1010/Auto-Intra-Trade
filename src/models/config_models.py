"""Configuration models for the backtest engine."""

from __future__ import annotations

from datetime import time

from pydantic import BaseModel, ConfigDict, Field

from src.utils.enums import ExecutionModel


class ChargesConfig(BaseModel):
    """Charge-rate configuration for round-trip trade costs."""

    model_config = ConfigDict(extra="forbid")

    brokerage_cap_per_order: float = Field(ge=0)
    brokerage_pct: float = Field(ge=0)
    stt_sell_pct: float = Field(ge=0)
    transaction_pct: float = Field(ge=0)
    gst_pct: float = Field(ge=0)
    sebi_pct: float = Field(ge=0)
    stamp_duty_buy_pct: float = Field(ge=0)


class StrategyConfig(BaseModel):
    """Strategy and risk parameter configuration."""

    model_config = ConfigDict(extra="forbid")

    atr_period: int = Field(gt=0)
    sensitivity: int = Field(gt=0)
    hard_sl_atr_multiplier: float = Field(gt=0)
    risk_per_trade_pct: float = Field(gt=0)
    allow_short: bool
    warmup_bars_5m: int = Field(ge=0)
    warmup_bars_15m: int = Field(ge=0)
    warmup_bars_1d: int = Field(ge=0)


class ExecutionConfig(BaseModel):
    """Execution behavior and session timing configuration."""

    model_config = ConfigDict(extra="forbid")

    entry_model: ExecutionModel
    exit_model: ExecutionModel
    slippage_pct: float = Field(ge=0)
    entry_cutoff_time: time
    forced_exit_time: time
    one_trade_at_a_time: bool
    same_candle_reentry_block: bool


class AppConfig(BaseModel):
    """Top-level application configuration."""

    model_config = ConfigDict(extra="forbid")

    charges: ChargesConfig
    strategy: StrategyConfig
    execution: ExecutionConfig
