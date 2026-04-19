"""Unit tests for SQLite database layer."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from src.db.repository import CandleRepository, TradeRepository
from src.db.schema import create_all_tables
from src.db.sqlite_service import connection_context, get_connection
from src.models.candle import Candle
from src.models.trade import RejectedTrade, Trade
from src.utils.enums import EntryTF, ExitReason, TradeSide

IST = ZoneInfo("Asia/Kolkata")


@pytest.mark.parametrize("db_path", [":memory:"])
def test_create_all_tables_creates_expected_tables(db_path: str) -> None:
    """Schema creation produces all expected table names."""
    with connection_context(db_path) as conn:
        create_all_tables(conn)

        rows = conn.execute(
            """
            SELECT name FROM sqlite_master
            WHERE type='table'
              AND name IN (
                'candles', 'signals', 'trades', 'rejected_trades', 'run_summaries'
              )
            """
        ).fetchall()

    found = {name for (name,) in rows}
    assert found == {"candles", "signals", "trades", "rejected_trades", "run_summaries"}


def test_insert_and_fetch_candles_roundtrip(tmp_path: Path) -> None:
    """Inserted candles roundtrip through repository fetch."""
    db_path = tmp_path / "candles.db"
    conn = get_connection(db_path)
    create_all_tables(conn)

    candles = [
        Candle(
            symbol="RELIANCE",
            timeframe="5m",
            timestamp=datetime(2026, 4, 19, 9, 15, tzinfo=IST),
            open=100.0,
            high=101.0,
            low=99.0,
            close=100.5,
            volume=1000.0,
        ),
        Candle(
            symbol="RELIANCE",
            timeframe="5m",
            timestamp=datetime(2026, 4, 19, 9, 20, tzinfo=IST),
            open=100.5,
            high=101.2,
            low=100.1,
            close=101.0,
            volume=1200.0,
        ),
    ]

    CandleRepository.insert_candles(conn, candles)
    fetched = CandleRepository.fetch_candles(
        conn=conn,
        symbol="RELIANCE",
        timeframe="5m",
        since=datetime(2026, 4, 19, 9, 15, tzinfo=IST),
        until=datetime(2026, 4, 19, 9, 20, tzinfo=IST),
    )

    conn.close()

    assert len(fetched) == 2
    assert fetched[0].timestamp == candles[0].timestamp
    assert fetched[1].close == candles[1].close


def test_insert_trade_and_fetch_by_run_id() -> None:
    """Inserted trades can be queried by run_id prefix."""
    conn = sqlite3.connect(":memory:")
    conn.execute("PRAGMA foreign_keys=ON;")
    create_all_tables(conn)

    entry_time = datetime(2026, 4, 19, 9, 20, tzinfo=IST)
    exit_time = datetime(2026, 4, 19, 10, 0, tzinfo=IST)
    trade = Trade(
        trade_id="20260419_103000_reliance_0001",
        symbol="RELIANCE",
        side=TradeSide.LONG,
        entry_tf=EntryTF.FIVE_MINUTE,
        entry_signal_time=entry_time,
        entry_time=entry_time,
        entry_signal_price=100.0,
        entry_price=100.1,
        quantity=10,
        hard_stop_price=98.0,
        exit_signal_time=exit_time,
        exit_time=exit_time,
        exit_signal_price=101.0,
        exit_price=100.9,
        exit_reason=ExitReason.TIME_EXIT,
        charges=5.0,
        gross_pnl=8.0,
        net_pnl=3.0,
        capital_before_trade=100000.0,
        capital_after_trade=100003.0,
        state_1d_at_entry="BUY",
        state_15m_at_entry="BUY",
        state_5m_at_entry="BUY",
    )

    TradeRepository.insert_trade(conn, trade)
    fetched = TradeRepository.fetch_trades(conn, "20260419_103000_reliance")

    conn.close()

    assert len(fetched) == 1
    assert fetched[0].trade_id == trade.trade_id
    assert fetched[0].exit_reason == ExitReason.TIME_EXIT


def test_insert_rejected_trade() -> None:
    """Rejected trade rows are inserted into rejected_trades table."""
    conn = sqlite3.connect(":memory:")
    create_all_tables(conn)

    rejected_trade = RejectedTrade(
        symbol="RELIANCE",
        timestamp=datetime(2026, 4, 19, 9, 25, tzinfo=IST),
        timeframe="5m",
        requested_side="LONG",
        reason="Quantity computed as zero",
    )

    TradeRepository.insert_rejected_trade(conn, rejected_trade)

    row = conn.execute(
        """
        SELECT symbol, timeframe, requested_side, reason
        FROM rejected_trades
        """
    ).fetchone()
    conn.close()

    assert row == (
        rejected_trade.symbol,
        rejected_trade.timeframe,
        rejected_trade.requested_side,
        rejected_trade.reason,
    )
