"""Tests for the owners table and the owner-migration.

Run: python tests/test_owners.py
"""

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp(prefix="graveyard-owners-"))
DB = TMP / "test.db"
os.environ["GRAVEYARD_DB"] = str(DB)

from graveyard.database import get_connection, init_db  # noqa: E402

PASS, FAIL = [], []

OLD_GRAVES = """
CREATE TABLE sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL, description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')));
CREATE TABLE graves (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    plot_number TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'available'
           CHECK (status IN ('available','reserved','occupied')),
    owner_name TEXT, owner_contact TEXT, notes TEXT,
    grave_ref TEXT NOT NULL DEFAULT '', deed_id TEXT NOT NULL DEFAULT '',
    date_purchased TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (section_id, plot_number));
"""


def check(name, fn):
    try:
        fn()
    except Exception as exc:
        FAIL.append(f"{name}: {type(exc).__name__}: {exc}")
    else:
        PASS.append(name)


def ok(res):
    assert res["ok"], f"expected ok, got error: {res.get('error')}"
    return res["data"]


def _build_old_db():
    """A pre-owners database: a duplicate name with two contacts, and a blank."""
    if DB.exists():
        DB.unlink()
    conn = sqlite3.connect(DB)
    conn.executescript(OLD_GRAVES)
    conn.execute("INSERT INTO sections (code, name) VALUES ('A','Garden')")
    for plot, name, contact in [
        ("1", "Aftab Dar", "222-444-777"),      # lowest id wins
        ("2", "Aftab Dar", "222-555-7777"),     # discarded
        ("3", "Margaret Whitfield", "555-0142"),
        ("4", "", ""),                           # stays unassigned
    ]:
        conn.execute(
            "INSERT INTO graves (section_id, plot_number, owner_name, owner_contact)"
            " VALUES (1, ?, ?, ?)", (plot, name, contact))
    conn.commit()
    conn.close()


def t_migration_creates_owners_and_dedupes():
    _build_old_db()
    init_db()
    with get_connection() as c:
        owners = [dict(r) for r in c.execute("SELECT * FROM owners ORDER BY name")]
        graves = [dict(r) for r in c.execute(
            "SELECT plot_number, owner_id FROM graves ORDER BY plot_number")]
        cols = {r["name"] for r in c.execute("PRAGMA table_info(graves)")}

    assert [o["name"] for o in owners] == ["Aftab Dar", "Margaret Whitfield"], owners
    aftab = owners[0]
    assert aftab["contact"] == "222-444-777", f"first contact must win: {aftab}"

    by_plot = {g["plot_number"]: g["owner_id"] for g in graves}
    assert by_plot["1"] == aftab["id"] and by_plot["2"] == aftab["id"], by_plot
    assert by_plot["4"] is None, "blank owner must stay unassigned"
    assert "owner_name" not in cols and "owner_contact" not in cols, cols


def t_migration_is_idempotent():
    _build_old_db()
    init_db()
    init_db()
    with get_connection() as c:
        n = c.execute("SELECT COUNT(*) c FROM owners").fetchone()["c"]
    assert n == 2, f"second init_db duplicated owners: {n}"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("t_"):
            check(name[2:], fn)
    for n in PASS:
        print(f"  [PASS] {n}")
    for f in FAIL:
        print(f"  [FAIL] {f}")
    print(f"RESULT {len(PASS)}/{len(PASS) + len(FAIL)} passed")
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if FAIL else 0)
