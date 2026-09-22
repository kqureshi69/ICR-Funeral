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


def _migrate_owners(conn) -> None:
    """Fold free-text grave ownership into first-class owner records."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(graves)")}
    if not cols or "owner_id" in cols:
        return  # graves not created yet, or already migrated

    if tuple(map(int, sqlite3.sqlite_version.split("."))) < (3, 35, 0):
        raise RuntimeError(
            f"SQLite {sqlite3.sqlite_version} cannot DROP COLUMN; 3.35+ required."
        )

    conn.execute("ALTER TABLE graves ADD COLUMN owner_id INTEGER REFERENCES owners(id)")

    # SQLite guarantees bare columns in a MIN() aggregate come from the matching
    # row, so `contact` here is the one from the lowest-id grave: first wins.
    duplicates = conn.execute(
        """SELECT TRIM(owner_name) AS name, owner_contact AS contact, MIN(id)
           FROM graves
           WHERE TRIM(COALESCE(owner_name, '')) <> ''
           GROUP BY TRIM(owner_name)"""
    ).fetchall()

    for row in duplicates:
        cur = conn.execute(
            "INSERT INTO owners (name, contact) VALUES (?, ?)",
            (row["name"], (row["contact"] or "").strip()),
        )
        conn.execute(
            "UPDATE graves SET owner_id = ? WHERE TRIM(owner_name) = ?",
            (cur.lastrowid, row["name"]),
        )

    conn.execute("ALTER TABLE graves DROP COLUMN owner_name")
    conn.execute("ALTER TABLE graves DROP COLUMN owner_contact")


def _ensure_indexes(conn) -> None:
    """Indexes that cannot live in schema.sql because they postdate a column."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(graves)")}
    if "owner_id" in cols:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_graves_owner ON graves(owner_id)")


def init_db() -> None:
    """Create tables from schema.sql if absent, then bring them up to date."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)
        _apply_migrations(conn)
        _migrate_owners(conn)
        _ensure_indexes(conn)
