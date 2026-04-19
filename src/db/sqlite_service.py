"""Connection utilities for SQLite storage."""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path


def get_connection(db_path: Path | str) -> sqlite3.Connection:
    """Create a configured SQLite connection.

    Args:
        db_path: SQLite file path or ":memory:".

    Returns:
        Configured SQLite connection with WAL and foreign keys enabled.
    """
    conn = sqlite3.connect(str(db_path))
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


@contextmanager
def connection_context(db_path: Path | str) -> Iterator[sqlite3.Connection]:
    """Provide a managed SQLite connection lifecycle.

    Args:
        db_path: SQLite file path or ":memory:".

    Yields:
        Configured SQLite connection.
    """
    conn = get_connection(db_path)
    try:
        yield conn
    finally:
        conn.close()
