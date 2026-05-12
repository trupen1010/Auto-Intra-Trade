"""Shared pytest fixtures for the Auto-Intra-Trade test suite."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import pytest

from src.db.schema import create_all_tables
from src.models.backtest_config import BacktestConfig, ChargesConfig
from src.models.candle import Candle

IST = ZoneInfo("Asia/Kolkata")


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_conn() -> sqlite3.Connection:
    """Provide an in-memory SQLite connection with schema initialised."""
    conn = sqlite3.connect(":memory:")
    create_all_tables(conn)
    yield conn
    conn.close()


# ---------------------------------------------------------------------------
# Candle factories
# ---------------------------------------------------------------------------


def make_candle(
    symbol: str = "TEST",
    timeframe: str = "5m",
    timestamp: datetime | None = None,
    open: float = 100.0,
    high: float = 105.0,
    low: float = 98.0,
    close: float = 102.0,
    volume: float = 1000.0,
) -> Candle:
    """Create a single Candle with sensible defaults."""
    if timestamp is None:
        timestamp = datetime(2024, 1, 15, 9, 20, 0, tzinfo=IST)
    return Candle(
        symbol=symbol,
        timeframe=timeframe,
        timestamp=timestamp,
        open=open,
        high=high,
        low=low,
        close=close,
        volume=volume,
    )


def make_candle_series(
    n: int,
    symbol: str = "TEST",
    timeframe: str = "5m",
    start_hour: int = 9,
    start_minute: int = 15,
    interval_minutes: int = 5,
    base_price: float = 100.0,
) -> list[Candle]:
    """Create a list of n sequential Candle objects at fixed intervals."""
    candles = []
    base_ts = datetime(2024, 1, 15, start_hour, start_minute, 0, tzinfo=IST)
    for i in range(n):
        ts = base_ts + timedelta(minutes=i * interval_minutes)
        price = base_price + i
        candles.append(
            Candle(
                symbol=symbol,
                timeframe=timeframe,
                timestamp=ts,
                open=price,
                high=price + 2.0,
                low=price - 1.0,
                close=price + 1.0,
                volume=500.0 + i * 10,
            )
        )
    return candles


@pytest.fixture
def sample_candle() -> Candle:
    """Single default Candle."""
    return make_candle()


@pytest.fixture
def sample_candles_5m() -> list[Candle]:
    """Series of 20 five-minute candles (one intraday session approx)."""
    return make_candle_series(20, timeframe="5m")


@pytest.fixture
def sample_candles_15m() -> list[Candle]:
    """Series of 10 fifteen-minute candles."""
    return make_candle_series(10, timeframe="15m", interval_minutes=15)


@pytest.fixture
def sample_candles_1d() -> list[Candle]:
    """Series of 30 daily candles."""
    candles = []
    base_ts = datetime(2024, 1, 2, 0, 0, 0, tzinfo=IST)
    for i in range(30):
        ts = base_ts + timedelta(days=i)
        price = 18000.0 + i * 50
        candles.append(
            Candle(
                symbol="TEST",
                timeframe="1d",
                timestamp=ts,
                open=price,
                high=price + 100,
                low=price - 80,
                close=price + 40,
                volume=100000.0,
            )
        )
    return candles


# ---------------------------------------------------------------------------
# Config fixture
# ---------------------------------------------------------------------------

_DEFAULT_CHARGES = ChargesConfig(
    brokerage_pct=0.0003,
    brokerage_cap_per_order=20.0,
    stt_sell_pct=0.00025,
    transaction_pct=0.0000335,
    sebi_pct=0.000001,
    gst_pct=0.18,
    stamp_duty_buy_pct=0.00003,
)


@pytest.fixture
def default_config() -> BacktestConfig:
    """A minimal valid BacktestConfig for use in unit and integration tests."""
    return BacktestConfig(
        run_id="test-run-001",
        symbol="TEST",
        start_date=date(2024, 1, 1),
        end_date=date(2024, 3, 31),
        initial_capital=100_000.0,
        risk_per_trade_pct=0.01,
        sl_atr_multiplier=1.5,
        atr_period=14,
        atr_sensitivity=2,
        entry_cutoff_time=time(15, 0),
        session_end_time=time(15, 30),
        charges=_DEFAULT_CHARGES,
    )
