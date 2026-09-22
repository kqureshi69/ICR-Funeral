"""Tests for the grave reference fields and the graves-table migration.

Run: python tests/test_graves.py
"""

import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TMP = Path(tempfile.mkdtemp(prefix="graveyard-graves-"))
DB = TMP / "test.db"
os.environ["GRAVEYARD_DB"] = str(DB)

from graveyard.api import Api                        # noqa: E402
from graveyard.database import get_connection, init_db  # noqa: E402

PASS, FAIL = [], []

# The graves table as it existed before the reference fields were added.
OLD_SCHEMA = """
CREATE TABLE sections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    description TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE TABLE graves (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id    INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    plot_number   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'available'
                  CHECK (status IN ('available', 'reserved', 'occupied')),
    owner_name    TEXT,
    owner_contact TEXT,
    notes         TEXT,
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (section_id, plot_number)
);
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


def fresh():
    """Empty, current-schema database with one section."""
    if DB.exists():
        DB.unlink()
    init_db()
    a = Api()
    return a, ok(a.create_section("A", "Garden"))


# --- tests ------------------------------------------------------------------

def t_new_fields_round_trip():
    a, sid = fresh()
    oid = ok(a.create_owner("M. Whitfield", "555-0142"))
    gid = ok(a.create_grave(sid, "1", "reserved", oid,
                            "Family plot", "GRV-00412", "DEED-77", "2019-04-02"))
    g = ok(a.get_grave(gid))
    assert g["grave_ref"] == "GRV-00412", g
    assert g["deed_id"] == "DEED-77", g
    assert g["date_purchased"] == "2019-04-02", g


def t_fields_are_optional():
    a, sid = fresh()
    gid = ok(a.create_grave(sid, "1"))
    g = ok(a.get_grave(gid))
    for f in ("grave_ref", "deed_id", "date_purchased"):
        assert g[f] == "", f"{f} should default to empty, got {g[f]!r}"


def t_update_changes_new_fields():
    a, sid = fresh()
    gid = ok(a.create_grave(sid, "1"))
    ok(a.update_grave(gid, sid, "1", "available", None,
                      "", "GRV-9", "DEED-9", "2020-01-01"))
    g = ok(a.get_grave(gid))
    assert (g["grave_ref"], g["deed_id"], g["date_purchased"]) \
        == ("GRV-9", "DEED-9", "2020-01-01"), g


def t_list_graves_exposes_new_fields():
    a, sid = fresh()
    ok(a.create_grave(sid, "1", "available", None, "", "GRV-1", "D-1", "2021-06-01"))
    row = ok(a.list_graves())[0]
    assert row["grave_ref"] == "GRV-1" and row["deed_id"] == "D-1", row


def t_search_matches_grave_ref():
    a, sid = fresh()
    ok(a.create_grave(sid, "1", "available", None, "", "GRV-00412", "", ""))
    ok(a.create_grave(sid, "2"))
    found = ok(a.list_graves(None, "", "00412"))
    assert len(found) == 1 and found[0]["plot_number"] == "1", found


def t_search_matches_deed_id():
    a, sid = fresh()
    ok(a.create_grave(sid, "1", "available", None, "", "", "DEED-77", ""))
    ok(a.create_grave(sid, "2"))
    found = ok(a.list_graves(None, "", "DEED-77"))
    assert len(found) == 1 and found[0]["plot_number"] == "1", found


def t_migration_adds_columns_and_keeps_rows():
    """An existing database from before this change must upgrade in place."""
    if DB.exists():
        DB.unlink()
    conn = sqlite3.connect(DB)
    conn.executescript(OLD_SCHEMA)
    conn.execute("INSERT INTO sections (code, name) VALUES ('A', 'Garden')")
    conn.execute(
        """INSERT INTO graves (section_id, plot_number, status, owner_name, notes)
           VALUES (1, '7', 'occupied', 'Existing Owner', 'do not lose me')""")
    conn.commit()
    conn.close()

    init_db()  # must migrate rather than leave the old shape alone

    with get_connection() as c:
        cols = [r["name"] for r in c.execute("PRAGMA table_info(graves)")]
    for col in ("grave_ref", "deed_id", "date_purchased"):
        assert col in cols, f"{col} missing after migration; columns={cols}"

    g = ok(Api().list_graves())[0]
    assert g["plot_number"] == "7", g
    assert g["owner_name"] == "Existing Owner", g
    assert g["notes"] == "do not lose me", g
    assert g["status"] == "occupied", g


def t_migration_is_idempotent():
    init_db()
    init_db()  # second run must not raise "duplicate column name"
    with get_connection() as c:
        cols = [r["name"] for r in c.execute("PRAGMA table_info(graves)")]
    assert cols.count("grave_ref") == 1, cols


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
