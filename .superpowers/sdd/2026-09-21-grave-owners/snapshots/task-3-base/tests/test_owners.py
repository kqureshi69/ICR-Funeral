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
    """A pre-owners database exercising every "no owner" and dedupe path:
    a duplicate name with two contacts, a whitespace-padded duplicate of
    that same name, a blank name, a whitespace-only name, and a NULL name
    (the column is nullable in the old schema)."""
    if DB.exists():
        DB.unlink()
    conn = sqlite3.connect(DB)
    conn.executescript(OLD_GRAVES)
    conn.execute("INSERT INTO sections (code, name) VALUES ('A','Garden')")
    for plot, name, contact in [
        ("1", "Aftab Dar", "222-444-777"),        # lowest id wins
        ("2", "Aftab Dar", "222-555-7777"),       # discarded
        ("3", "Margaret Whitfield", "555-0142"),
        ("4", "", ""),                             # blank: stays unassigned
        ("5", " Aftab Dar ", "999-999-9999"),     # padded dupe: must merge via TRIM
        ("6", "   ", "111-111-1111"),             # whitespace-only: stays unassigned
    ]:
        conn.execute(
            "INSERT INTO graves (section_id, plot_number, owner_name, owner_contact)"
            " VALUES (1, ?, ?, ?)", (plot, name, contact))
    conn.execute(
        "INSERT INTO graves (section_id, plot_number, owner_name, owner_contact)"
        " VALUES (1, '7', NULL, NULL)")            # NULL name: stays unassigned
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
    assert by_plot["5"] == aftab["id"], "whitespace-padded duplicate must merge via TRIM"
    assert by_plot["4"] is None, "blank owner must stay unassigned"
    assert by_plot["6"] is None, "whitespace-only owner must stay unassigned"
    assert by_plot["7"] is None, "NULL owner must stay unassigned"
    assert "owner_name" not in cols and "owner_contact" not in cols, cols


def t_migration_is_idempotent():
    _build_old_db()
    init_db()
    with get_connection() as c:
        owners_before = [dict(r) for r in c.execute("SELECT * FROM owners ORDER BY name")]
        by_plot_before = {r["plot_number"]: r["owner_id"] for r in c.execute(
            "SELECT plot_number, owner_id FROM graves ORDER BY plot_number")}

    init_db()  # second run must not raise, duplicate, or reassign anything

    with get_connection() as c:
        owners_after = [dict(r) for r in c.execute("SELECT * FROM owners ORDER BY name")]
        by_plot_after = {r["plot_number"]: r["owner_id"] for r in c.execute(
            "SELECT plot_number, owner_id FROM graves ORDER BY plot_number")}

    assert len(owners_after) == 2, f"second init_db duplicated owners: {owners_after}"
    assert owners_after == owners_before, \
        f"owner rows changed across idempotent runs: {owners_before} -> {owners_after}"
    assert by_plot_after == by_plot_before, \
        f"owner_id assignments changed across idempotent runs: {by_plot_before} -> {by_plot_after}"


def t_migration_self_heals_after_interrupted_run():
    """ALTER TABLE ... ADD COLUMN is DDL and commits on its own under
    sqlite3's legacy transaction handling, outside the transaction carrying
    the backfill and the DROP COLUMNs. Simulate exactly that: a crash right
    after the ADD COLUMN commits but before anything else does, then confirm
    the next init_db() notices the unfinished migration and completes it
    instead of silently leaving the data unmigrated forever."""
    _build_old_db()

    # sqlite3.Connection is a C type: its methods can't be monkeypatched
    # in place. Instead, connect through a subclass (via the `factory`
    # kwarg) that raises right after the ADD COLUMN statement it just ran.
    class _CrashAfterAddColumn(sqlite3.Connection):
        _armed = False

        def execute(self, sql, *args, **kwargs):
            if _CrashAfterAddColumn._armed:
                raise RuntimeError("simulated crash mid-migration")
            if isinstance(sql, str) and sql.startswith(
                    "ALTER TABLE graves ADD COLUMN owner_id"):
                _CrashAfterAddColumn._armed = True
            return super().execute(sql, *args, **kwargs)

    orig_connect = sqlite3.connect

    def _connect_with_crash(*args, **kwargs):
        kwargs.setdefault("factory", _CrashAfterAddColumn)
        return orig_connect(*args, **kwargs)

    sqlite3.connect = _connect_with_crash
    try:
        try:
            init_db()
        except RuntimeError as exc:
            assert "simulated crash" in str(exc), exc
        else:
            raise AssertionError("expected the simulated crash to raise")
    finally:
        sqlite3.connect = orig_connect

    # Confirm the crash really did leave owner_id committed on its own while
    # everything after it rolled back -- i.e. that this test reproduces the
    # bug, not just exercises unreachable code.
    with sqlite3.connect(DB) as raw:
        raw.row_factory = sqlite3.Row
        cols = {r["name"] for r in raw.execute("PRAGMA table_info(graves)")}
    assert "owner_id" in cols, f"ADD COLUMN should have survived the rollback: {cols}"
    assert "owner_name" in cols, f"backfill/drop should have rolled back: {cols}"

    init_db()  # the next ordinary startup must finish the interrupted migration

    with get_connection() as c:
        owners = [dict(r) for r in c.execute("SELECT * FROM owners ORDER BY name")]
        graves = [dict(r) for r in c.execute(
            "SELECT plot_number, owner_id FROM graves ORDER BY plot_number")]
        cols = {r["name"] for r in c.execute("PRAGMA table_info(graves)")}

    assert [o["name"] for o in owners] == ["Aftab Dar", "Margaret Whitfield"], owners
    aftab = owners[0]
    by_plot = {g["plot_number"]: g["owner_id"] for g in graves}
    assert by_plot["1"] == aftab["id"] and by_plot["2"] == aftab["id"], by_plot
    assert by_plot["5"] == aftab["id"], by_plot
    assert by_plot["4"] is None and by_plot["6"] is None and by_plot["7"] is None, by_plot
    assert "owner_name" not in cols and "owner_contact" not in cols, cols


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
