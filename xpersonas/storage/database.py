"""SQLite database connection and migration management."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from xpersonas.core.exceptions import StorageError

_SCHEMA_PATH = Path(__file__).parent / "schema.sql"
_MIGRATIONS_PATH = Path(__file__).parent / "migrations"


class Database:
    """SQLite database with WAL mode and migration support."""

    def __init__(self, db_path: str | Path = "xpersonas.db"):
        self.db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None

    def connect(self) -> None:
        """Open connection with WAL mode and foreign keys."""
        try:
            self._conn = sqlite3.connect(str(self.db_path))
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA foreign_keys=ON")
            self._conn.execute("PRAGMA busy_timeout=5000")
        except sqlite3.Error as e:
            raise StorageError(f"Failed to connect to database: {e}") from e

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            raise StorageError("Database not connected. Call connect() first.")
        return self._conn

    def initialize(self) -> None:
        """Run schema.sql to create tables."""
        schema = _SCHEMA_PATH.read_text()
        self.conn.executescript(schema)

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        return self.conn.execute(sql, params)

    def executemany(self, sql: str, params: list[tuple[Any, ...]]) -> sqlite3.Cursor:
        return self.conn.executemany(sql, params)

    def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Row | None:
        return self.conn.execute(sql, params).fetchone()

    def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[sqlite3.Row]:
        return self.conn.execute(sql, params).fetchall()

    def commit(self) -> None:
        self.conn.commit()

    def __enter__(self) -> Database:
        self.connect()
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
