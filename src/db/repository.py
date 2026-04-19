"""Repository helpers for SQLite persistence."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

from src.models.candle import Candle
from src.models.trade import RejectedTrade, Trade

IST = ZoneInfo("Asia/Kolkata")


def _to_unix_ms(dt: datetime) -> int:
    """Convert a timezone-aware datetime to unix milliseconds.

    Args:
        dt: Datetime to convert.

    Returns:
        Unix timestamp in milliseconds.
    """
    return int(dt.timestamp() * 1000)


def _from_unix_ms(timestamp_ms: int) -> datetime:
    """Convert unix milliseconds to IST datetime.

    Args:
        timestamp_ms: Unix timestamp in milliseconds.

    Returns:
        Timezone-aware Asia/Kolkata datetime.
    """
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=IST)


class CandleRepository:
    """Persistence operations for candle records."""

    @staticmethod
    def insert_candles(conn: sqlite3.Connection, candles: list[Candle]) -> None:
        """Insert candles in bulk, ignoring duplicates.

        Args:
            conn: Open SQLite connection.
            candles: Candle rows to persist.
        """
        if not candles:
            return

        rows = [
            (
                candle.symbol,
                candle.timeframe,
                _to_unix_ms(candle.timestamp),
                candle.open,
                candle.high,
                candle.low,
                candle.close,
                candle.volume,
            )
            for candle in candles
        ]
        conn.executemany(
            """
            INSERT OR IGNORE INTO candles (
                symbol, timeframe, timestamp, open, high, low, close, volume
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )
        conn.commit()

    @staticmethod
    def fetch_candles(
        conn: sqlite3.Connection,
        symbol: str,
        timeframe: str,
        since: datetime,
        until: datetime,
    ) -> list[Candle]:
        """Fetch candles for a symbol/timeframe within a timestamp range.

        Args:
            conn: Open SQLite connection.
            symbol: Instrument symbol.
            timeframe: Candle timeframe string.
            since: Inclusive lower bound for candle timestamp.
            until: Inclusive upper bound for candle timestamp.

        Returns:
            Ordered candle list.
        """
        cursor = conn.execute(
            """
            SELECT symbol, timeframe, timestamp, open, high, low, close, volume
            FROM candles
            WHERE symbol = ?
              AND timeframe = ?
              AND timestamp >= ?
              AND timestamp <= ?
            ORDER BY timestamp ASC
            """,
            (symbol, timeframe, _to_unix_ms(since), _to_unix_ms(until)),
        )
        rows = cursor.fetchall()
        return [
            Candle(
                symbol=row[0],
                timeframe=row[1],
                timestamp=_from_unix_ms(row[2]),
                open=row[3],
                high=row[4],
                low=row[5],
                close=row[6],
                volume=row[7],
            )
            for row in rows
        ]


class TradeRepository:
    """Persistence operations for trades and rejected trades."""

    @staticmethod
    def insert_trade(conn: sqlite3.Connection, trade: Trade) -> None:
        """Insert a completed or active trade row.

        Args:
            conn: Open SQLite connection.
            trade: Trade to persist.
        """
        conn.execute(
            """
            INSERT INTO trades (
                trade_id, symbol, side, entry_tf, entry_signal_time, entry_time,
                entry_signal_price, entry_price, quantity, hard_stop_price,
                exit_signal_time, exit_time, exit_signal_price, exit_price,
                exit_reason, charges, gross_pnl, net_pnl, capital_before_trade,
                capital_after_trade, state_1d_at_entry, state_15m_at_entry,
                state_5m_at_entry
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                trade.trade_id,
                trade.symbol,
                str(trade.side),
                str(trade.entry_tf),
                _to_unix_ms(trade.entry_signal_time),
                _to_unix_ms(trade.entry_time),
                trade.entry_signal_price,
                trade.entry_price,
                trade.quantity,
                trade.hard_stop_price,
                _to_unix_ms(trade.exit_signal_time) if trade.exit_signal_time else None,
                _to_unix_ms(trade.exit_time) if trade.exit_time else None,
                trade.exit_signal_price,
                trade.exit_price,
                str(trade.exit_reason) if trade.exit_reason else None,
                trade.charges,
                trade.gross_pnl,
                trade.net_pnl,
                trade.capital_before_trade,
                trade.capital_after_trade,
                trade.state_1d_at_entry,
                trade.state_15m_at_entry,
                trade.state_5m_at_entry,
            ),
        )
        conn.commit()

    @staticmethod
    def insert_rejected_trade(conn: sqlite3.Connection, rt: RejectedTrade) -> None:
        """Insert a rejected trade row.

        Args:
            conn: Open SQLite connection.
            rt: Rejected trade to persist.
        """
        conn.execute(
            """
            INSERT INTO rejected_trades (
                symbol, timestamp, timeframe, requested_side, reason
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (rt.symbol, _to_unix_ms(rt.timestamp), rt.timeframe, rt.requested_side, rt.reason),
        )
        conn.commit()

    @staticmethod
    def fetch_trades(conn: sqlite3.Connection, run_id: str) -> list[Trade]:
        """Fetch trades associated with a run identifier.

        Args:
            conn: Open SQLite connection.
            run_id: Run identifier prefix used in trade_id values.

        Returns:
            Ordered trade list.
        """
        cursor = conn.execute(
            """
            SELECT
                trade_id, symbol, side, entry_tf, entry_signal_time, entry_time,
                entry_signal_price, entry_price, quantity, hard_stop_price,
                exit_signal_time, exit_time, exit_signal_price, exit_price,
                exit_reason, charges, gross_pnl, net_pnl, capital_before_trade,
                capital_after_trade, state_1d_at_entry, state_15m_at_entry,
                state_5m_at_entry
            FROM trades
            WHERE trade_id LIKE ?
            ORDER BY entry_time ASC
            """,
            (f"{run_id}%",),
        )
        rows = cursor.fetchall()
        return [
            Trade(
                trade_id=row[0],
                symbol=row[1],
                side=row[2],
                entry_tf=row[3],
                entry_signal_time=_from_unix_ms(row[4]),
                entry_time=_from_unix_ms(row[5]),
                entry_signal_price=row[6],
                entry_price=row[7],
                quantity=row[8],
                hard_stop_price=row[9],
                exit_signal_time=_from_unix_ms(row[10]) if row[10] is not None else None,
                exit_time=_from_unix_ms(row[11]) if row[11] is not None else None,
                exit_signal_price=row[12],
                exit_price=row[13],
                exit_reason=row[14],
                charges=row[15],
                gross_pnl=row[16],
                net_pnl=row[17],
                capital_before_trade=row[18],
                capital_after_trade=row[19],
                state_1d_at_entry=row[20],
                state_15m_at_entry=row[21],
                state_5m_at_entry=row[22],
            )
            for row in rows
        ]


class RunRepository:
    """Persistence operations for run summary records."""

    @staticmethod
    def insert_run_summary(conn: sqlite3.Connection, summary: dict) -> None:
        """Insert or replace a run summary.

        Args:
            conn: Open SQLite connection.
            summary: Run summary mapping.
        """
        conn.execute(
            """
            INSERT OR REPLACE INTO run_summaries (
                run_id, symbol, start_ts, end_ts, total_trades,
                winning_trades, net_pnl, config_snapshot
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                summary["run_id"],
                summary["symbol"],
                summary["start_ts"],
                summary["end_ts"],
                summary["total_trades"],
                summary["winning_trades"],
                summary["net_pnl"],
                summary["config_snapshot"],
            ),
        )
        conn.commit()
