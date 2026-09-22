"""SQLite connection handling, schema initialisation and migrations."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path

# Project root is the parent of this package directory.
ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"

# Allow the DB location to be overridden for tests / packaging.
DB_PATH = Path(os.environ.get("GRAVEYARD_DB", DATA_DIR / "graveyard.db"))

# Columns added after the first release. ``CREATE TABLE IF NOT EXISTS`` leaves
# existing databases untouched, so each one is applied with ALTER TABLE.
# Appending here is all a future column needs.
MIGRATIONS: dict[str, dict[str, str]] = {
    "graves": {
        "grave_ref": "TEXT NOT NULL DEFAULT ''",
        "deed_id": "TEXT NOT NULL DEFAULT ''",
        "date_purchased": "TEXT NOT NULL DEFAULT ''",
    },
}


@contextmanager
def get_connection():
    """A connection with foreign keys on and rows accessible by name.

    Commits on success, rolls back on error, and always closes: an unclosed
    connection keeps a file handle on the database, which on Windows blocks
    the file from being replaced or removed.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def _apply_migrations(conn) -> None:
    """Add any columns missing from an older database. Idempotent."""
    for table, columns in MIGRATIONS.items():
        existing = {r["name"] for r in conn.execute(f"PRAGMA table_info({table})")}
        if not existing:
            continue  # table not created yet; the schema script owns it
        for name, spec in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {spec}")


def init_db() -> None:
    """Create tables from schema.sql if absent, then bring them up to date."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)
        _apply_migrations(conn)
