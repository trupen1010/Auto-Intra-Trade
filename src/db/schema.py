"""SQLite schema definitions for the backtest engine."""

from __future__ import annotations

import sqlite3

CANDLES_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS candles (
    id INTEGER PRIMARY KEY,
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    timestamp INTEGER NOT NULL,
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
    candle_close_time INTEGER NOT NULL,
    side TEXT NOT NULL,
    trailing_stop REAL,
    close_price REAL NOT NULL
);
"""

TRADES_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS trades (
    id INTEGER PRIMARY KEY,
    trade_id TEXT NOT NULL,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    entry_tf TEXT NOT NULL,
    entry_signal_time INTEGER NOT NULL,
    entry_time INTEGER NOT NULL,
    entry_signal_price REAL NOT NULL,
    entry_price REAL NOT NULL,
    quantity INTEGER NOT NULL,
    hard_stop_price REAL NOT NULL,
    exit_signal_time INTEGER,
    exit_time INTEGER,
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
    timestamp INTEGER NOT NULL,
    timeframe TEXT NOT NULL,
    requested_side TEXT NOT NULL,
    reason TEXT NOT NULL
);
"""

RUN_SUMMARIES_TABLE_DDL = """
CREATE TABLE IF NOT EXISTS run_summaries (
    run_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    start_ts INTEGER NOT NULL,
    end_ts INTEGER NOT NULL,
    total_trades INTEGER NOT NULL,
    winning_trades INTEGER NOT NULL,
    net_pnl REAL NOT NULL,
    config_snapshot TEXT NOT NULL
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
                RUN_SUMMARIES_TABLE_DDL,
            )
        )
    )
    conn.commit()
