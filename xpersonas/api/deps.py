"""Dependency injection for API routes."""

from __future__ import annotations

from xpersonas.storage.database import Database

_db: Database | None = None


def init_db(db_path: str = "xpersonas.db") -> Database:
    global _db
    _db = Database(db_path)
    _db.connect()
    _db.initialize()
    return _db


def get_db() -> Database:
    if _db is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    return _db
