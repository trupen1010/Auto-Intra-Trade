"""Backtest configuration models with validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time


@dataclass(frozen=True, slots=True)
class ChargesConfig:
    """Commission and fee structure for trades.

    All percentages are expressed as decimals (e.g., 0.0003 = 0.03%).
    Brokerage has a per-order cap; others apply per turnover.
    """

    brokerage_pct: float
    brokerage_cap_per_order: float
    stt_sell_pct: float
    transaction_pct: float
    sebi_pct: float
    gst_pct: float
    stamp_duty_buy_pct: float

    def __post_init__(self) -> None:
        """Validate charge percentages are non-negative."""
        if not all(
            v >= 0
            for v in [
                self.brokerage_pct,
                self.brokerage_cap_per_order,
                self.stt_sell_pct,
                self.transaction_pct,
                self.sebi_pct,
                self.gst_pct,
                self.stamp_duty_buy_pct,
            ]
        ):
            raise ValueError("All charge values must be non-negative")


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """Complete backtest configuration.

    User-supplied parameters and computed runtime state (ATR arrays, trailing stops).
    All timestamps are timezone-aware (Asia/Kolkata).
    """

    run_id: str
    symbol: str
    start_date: date
    end_date: date
    initial_capital: float
    risk_per_trade_pct: float
    sl_atr_multiplier: float
    atr_period: int
    atr_sensitivity: int
    entry_cutoff_time: time
    session_end_time: time
    charges: ChargesConfig
    atr_values_5m: list[float] = field(default_factory=list)
    trailing_stop_5m: list[float | None] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate all configuration parameters."""
        if self.initial_capital <= 0:
            raise ValueError("initial_capital must be positive")
        if not (0 < self.risk_per_trade_pct < 1):
            raise ValueError("risk_per_trade_pct must be in (0, 1)")
        if self.sl_atr_multiplier <= 0:
            raise ValueError("sl_atr_multiplier must be positive")
        if self.atr_period <= 0:
            raise ValueError("atr_period must be positive")
        if self.atr_sensitivity <= 0:
            raise ValueError("atr_sensitivity must be positive")
        if self.start_date >= self.end_date:
            raise ValueError("start_date must be before end_date")
        if self.entry_cutoff_time >= self.session_end_time:
            raise ValueError("entry_cutoff_time must be before session_end_time")

    @classmethod
    def from_dict(cls, d: dict, run_id: str, symbol: str) -> BacktestConfig:
        """Create config from dictionary with validation.

        Args:
            d: Configuration dictionary with required and optional keys.
            run_id: Unique run identifier (typically uuid4).
            symbol: Instrument symbol.

        Returns:
            Validated BacktestConfig instance.

        Raises:
            ValueError: If required keys missing or values invalid.
            TypeError: If value types are incompatible.
        """
        required = {
            "initial_capital",
            "risk_per_trade_pct",
            "sl_atr_multiplier",
            "atr_period",
            "atr_sensitivity",
            "start_date",
            "end_date",
            "entry_cutoff_time",
            "session_end_time",
            "charges",
        }
        missing = required - set(d.keys())
        if missing:
            raise ValueError(f"Missing required config keys: {missing}")

        charges_dict = d.get("charges")
        if not isinstance(charges_dict, dict):
            raise TypeError("charges must be a dictionary")

        try:
            charges = ChargesConfig(**charges_dict)
        except TypeError as e:
            raise ValueError(f"Invalid charges config: {e}") from e

        try:
            return cls(
                run_id=run_id,
                symbol=symbol,
                start_date=d["start_date"],
                end_date=d["end_date"],
                initial_capital=float(d["initial_capital"]),
                risk_per_trade_pct=float(d["risk_per_trade_pct"]),
                sl_atr_multiplier=float(d["sl_atr_multiplier"]),
                atr_period=int(d["atr_period"]),
                atr_sensitivity=int(d["atr_sensitivity"]),
                entry_cutoff_time=d["entry_cutoff_time"],
                session_end_time=d["session_end_time"],
                charges=charges,
            )
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid config value: {e}") from e
