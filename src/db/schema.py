"""SQLite schema definitions for the backtest engine."""

from __future__ import annotations

import sqlite3

CANDLES_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS candles (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp TEXT NOT NULL, -- ISO 8601
    open REAL NOT NULL,
    high REAL NOT NULL,
    low REAL NOT NULL,
    close REAL NOT NULL,
    volume REAL NOT NULL,
    UNIQUE(symbol, timeframe, timestamp)
);
"""

SIGNALS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS signals (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    candle_close_time TEXT NOT NULL, -- ISO 8601
    side TEXT NOT NULL,
    trailing_stop REAL,
    close_price REAL NOT NULL,
    UNIQUE(symbol, timeframe, candle_close_time)
);
"""

TRADES_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS trades (
    trade_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    entry_tf TEXT NOT NULL,
    entry_signal_time TEXT NOT NULL, -- ISO 8601
    entry_time TEXT NOT NULL, -- ISO 8601
    entry_signal_price REAL NOT NULL,
    entry_price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    hard_stop_price REAL NOT NULL,
    exit_signal_time TEXT, -- ISO 8601
    exit_time TEXT, -- ISO 8601
    exit_signal_price REAL,
    exit_price REAL,
    exit_reason TEXT,
    charges REAL NOT NULL,
    gross_pnl REAL NOT NULL,
    net_pnl REAL NOT NULL,
    capital_before_trade REAL NOT NULL,
    capital_after_trade REAL NOT NULL,
    state_1d_at_entry TEXT NOT NULL,
    state_15m_at_entry TEXT NOT NULL,
    state_5m_at_entry TEXT NOT NULL
);
"""

REJECTED_TRADES_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS rejected_trades (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timestamp TEXT NOT NULL, -- ISO 8601
    timeframe TEXT NOT NULL,
    requested_side TEXT NOT NULL,
    reason TEXT NOT NULL
);
"""

BACKTEST_RUNS_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS backtest_runs (
    run_id TEXT PRIMARY KEY,
    started_at TEXT NOT NULL, -- ISO 8601
    finished_at TEXT, -- ISO 8601
    config_snapshot TEXT NOT NULL,
    symbols TEXT NOT NULL,
    date_from TEXT NOT NULL,
    date_to TEXT NOT NULL,
    total_trades INTEGER DEFAULT 0,
    net_profit REAL DEFAULT 0,
    max_drawdown REAL DEFAULT 0
);
"""


def create_all_tables(conn: sqlite3.Connection) -> None:
    """Create all database tables if they do not exist.

    Args:
        conn: Open SQLite connection.
    """
    conn.executescript(
        "\n".join(
            (
                CANDLES_TABLE_DDL,
                SIGNALS_TABLE_DDL,
                TRADES_TABLE_DDL,
                REJECTED_TRADES_TABLE_DDL,
                BACKTEST_RUNS_TABLE_DDL,
            )
        )
    )
    conn.commit()
