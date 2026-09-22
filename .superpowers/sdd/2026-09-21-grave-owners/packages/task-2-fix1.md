# Review package: task-2-fix1

No git in this project: this diff is snapshot-to-snapshot,
base `task-2-head` -> current working tree.

## Files changed

- graveyard/database.py
- tests/test_owners.py

## Stat

2 files, +129 / -16 lines

## Full diff

```diff
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-2-head/graveyard/database.py C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-2-fix1-head/graveyard/database.py
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-2-head/graveyard/database.py	2026-09-21 08:26:56.426990400 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-2-fix1-head/graveyard/database.py	2026-09-21 08:36:22.172210600 -0400
@@ -58,17 +58,30 @@
 
 
 def _migrate_owners(conn) -> None:
-    """Fold free-text grave ownership into first-class owner records."""
+    """Fold free-text grave ownership into first-class owner records.
+
+    Keyed on ``owner_name`` being present, not on ``owner_id`` being absent:
+    ``ALTER TABLE ... ADD COLUMN`` is DDL and, under sqlite3's legacy
+    transaction handling, commits immediately on its own -- outside the
+    transaction carrying the backfill and the two DROP COLUMNs. If a run is
+    interrupted after the ADD COLUMN but before the DROPs, ``owner_id``
+    survives the rollback while ``owner_name`` does not. Keying the "already
+    migrated" check on ``owner_id`` would then see that surviving column and
+    exit immediately, permanently losing the unmigrated ownership data.
+    Keying on ``owner_name`` still being there makes an interrupted run
+    self-heal on the very next ``init_db()`` instead.
+    """
     cols = {r["name"] for r in conn.execute("PRAGMA table_info(graves)")}
-    if not cols or "owner_id" in cols:
-        return  # graves not created yet, or already migrated
+    if not cols or "owner_name" not in cols:
+        return  # graves not created yet, or migration already committed
 
     if tuple(map(int, sqlite3.sqlite_version.split("."))) < (3, 35, 0):
         raise RuntimeError(
             f"SQLite {sqlite3.sqlite_version} cannot DROP COLUMN; 3.35+ required."
         )
 
-    conn.execute("ALTER TABLE graves ADD COLUMN owner_id INTEGER REFERENCES owners(id)")
+    if "owner_id" not in cols:
+        conn.execute("ALTER TABLE graves ADD COLUMN owner_id INTEGER REFERENCES owners(id)")
 
     # SQLite guarantees bare columns in a MIN() aggregate come from the matching
     # row, so `contact` here is the one from the lowest-id grave: first wins.
@@ -80,13 +93,23 @@
     ).fetchall()
 
     for row in duplicates:
-        cur = conn.execute(
-            "INSERT INTO owners (name, contact) VALUES (?, ?)",
-            (row["name"], (row["contact"] or "").strip()),
-        )
+        # A previously interrupted run may already have inserted some owners
+        # before it died; re-run must reuse them instead of violating the
+        # unique name index.
+        existing = conn.execute(
+            "SELECT id FROM owners WHERE name = ?", (row["name"],)
+        ).fetchone()
+        if existing:
+            owner_id = existing["id"]
+        else:
+            cur = conn.execute(
+                "INSERT INTO owners (name, contact) VALUES (?, ?)",
+                (row["name"], (row["contact"] or "").strip()),
+            )
+            owner_id = cur.lastrowid
         conn.execute(
             "UPDATE graves SET owner_id = ? WHERE TRIM(owner_name) = ?",
-            (cur.lastrowid, row["name"]),
+            (owner_id, row["name"]),
         )
 
     conn.execute("ALTER TABLE graves DROP COLUMN owner_name")
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-2-head/tests/test_owners.py C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-2-fix1-head/tests/test_owners.py
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-2-head/tests/test_owners.py	2026-09-21 08:26:37.911936300 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-2-fix1-head/tests/test_owners.py	2026-09-21 08:37:16.834245700 -0400
@@ -56,21 +56,29 @@
 
 
 def _build_old_db():
-    """A pre-owners database: a duplicate name with two contacts, and a blank."""
+    """A pre-owners database exercising every "no owner" and dedupe path:
+    a duplicate name with two contacts, a whitespace-padded duplicate of
+    that same name, a blank name, a whitespace-only name, and a NULL name
+    (the column is nullable in the old schema)."""
     if DB.exists():
         DB.unlink()
     conn = sqlite3.connect(DB)
     conn.executescript(OLD_GRAVES)
     conn.execute("INSERT INTO sections (code, name) VALUES ('A','Garden')")
     for plot, name, contact in [
-        ("1", "Aftab Dar", "222-444-777"),      # lowest id wins
-        ("2", "Aftab Dar", "222-555-7777"),     # discarded
+        ("1", "Aftab Dar", "222-444-777"),        # lowest id wins
+        ("2", "Aftab Dar", "222-555-7777"),       # discarded
         ("3", "Margaret Whitfield", "555-0142"),
-        ("4", "", ""),                           # stays unassigned
+        ("4", "", ""),                             # blank: stays unassigned
+        ("5", " Aftab Dar ", "999-999-9999"),     # padded dupe: must merge via TRIM
+        ("6", "   ", "111-111-1111"),             # whitespace-only: stays unassigned
     ]:
         conn.execute(
             "INSERT INTO graves (section_id, plot_number, owner_name, owner_contact)"
             " VALUES (1, ?, ?, ?)", (plot, name, contact))
+    conn.execute(
+        "INSERT INTO graves (section_id, plot_number, owner_name, owner_contact)"
+        " VALUES (1, '7', NULL, NULL)")            # NULL name: stays unassigned
     conn.commit()
     conn.close()
 
@@ -90,17 +98,99 @@
 
     by_plot = {g["plot_number"]: g["owner_id"] for g in graves}
     assert by_plot["1"] == aftab["id"] and by_plot["2"] == aftab["id"], by_plot
+    assert by_plot["5"] == aftab["id"], "whitespace-padded duplicate must merge via TRIM"
     assert by_plot["4"] is None, "blank owner must stay unassigned"
+    assert by_plot["6"] is None, "whitespace-only owner must stay unassigned"
+    assert by_plot["7"] is None, "NULL owner must stay unassigned"
     assert "owner_name" not in cols and "owner_contact" not in cols, cols
 
 
 def t_migration_is_idempotent():
     _build_old_db()
     init_db()
-    init_db()
     with get_connection() as c:
-        n = c.execute("SELECT COUNT(*) c FROM owners").fetchone()["c"]
-    assert n == 2, f"second init_db duplicated owners: {n}"
+        owners_before = [dict(r) for r in c.execute("SELECT * FROM owners ORDER BY name")]
+        by_plot_before = {r["plot_number"]: r["owner_id"] for r in c.execute(
+            "SELECT plot_number, owner_id FROM graves ORDER BY plot_number")}
+
+    init_db()  # second run must not raise, duplicate, or reassign anything
+
+    with get_connection() as c:
+        owners_after = [dict(r) for r in c.execute("SELECT * FROM owners ORDER BY name")]
+        by_plot_after = {r["plot_number"]: r["owner_id"] for r in c.execute(
+            "SELECT plot_number, owner_id FROM graves ORDER BY plot_number")}
+
+    assert len(owners_after) == 2, f"second init_db duplicated owners: {owners_after}"
+    assert owners_after == owners_before, \
+        f"owner rows changed across idempotent runs: {owners_before} -> {owners_after}"
+    assert by_plot_after == by_plot_before, \
+        f"owner_id assignments changed across idempotent runs: {by_plot_before} -> {by_plot_after}"
+
+
+def t_migration_self_heals_after_interrupted_run():
+    """ALTER TABLE ... ADD COLUMN is DDL and commits on its own under
+    sqlite3's legacy transaction handling, outside the transaction carrying
+    the backfill and the DROP COLUMNs. Simulate exactly that: a crash right
+    after the ADD COLUMN commits but before anything else does, then confirm
+    the next init_db() notices the unfinished migration and completes it
+    instead of silently leaving the data unmigrated forever."""
+    _build_old_db()
+
+    # sqlite3.Connection is a C type: its methods can't be monkeypatched
+    # in place. Instead, connect through a subclass (via the `factory`
+    # kwarg) that raises right after the ADD COLUMN statement it just ran.
+    class _CrashAfterAddColumn(sqlite3.Connection):
+        _armed = False
+
+        def execute(self, sql, *args, **kwargs):
+            if _CrashAfterAddColumn._armed:
+                raise RuntimeError("simulated crash mid-migration")
+            if isinstance(sql, str) and sql.startswith(
+                    "ALTER TABLE graves ADD COLUMN owner_id"):
+                _CrashAfterAddColumn._armed = True
+            return super().execute(sql, *args, **kwargs)
+
+    orig_connect = sqlite3.connect
+
+    def _connect_with_crash(*args, **kwargs):
+        kwargs.setdefault("factory", _CrashAfterAddColumn)
+        return orig_connect(*args, **kwargs)
+
+    sqlite3.connect = _connect_with_crash
+    try:
+        try:
+            init_db()
+        except RuntimeError as exc:
+            assert "simulated crash" in str(exc), exc
+        else:
+            raise AssertionError("expected the simulated crash to raise")
+    finally:
+        sqlite3.connect = orig_connect
+
+    # Confirm the crash really did leave owner_id committed on its own while
+    # everything after it rolled back -- i.e. that this test reproduces the
+    # bug, not just exercises unreachable code.
+    with sqlite3.connect(DB) as raw:
+        raw.row_factory = sqlite3.Row
+        cols = {r["name"] for r in raw.execute("PRAGMA table_info(graves)")}
+    assert "owner_id" in cols, f"ADD COLUMN should have survived the rollback: {cols}"
+    assert "owner_name" in cols, f"backfill/drop should have rolled back: {cols}"
+
+    init_db()  # the next ordinary startup must finish the interrupted migration
+
+    with get_connection() as c:
+        owners = [dict(r) for r in c.execute("SELECT * FROM owners ORDER BY name")]
+        graves = [dict(r) for r in c.execute(
+            "SELECT plot_number, owner_id FROM graves ORDER BY plot_number")]
+        cols = {r["name"] for r in c.execute("PRAGMA table_info(graves)")}
+
+    assert [o["name"] for o in owners] == ["Aftab Dar", "Margaret Whitfield"], owners
+    aftab = owners[0]
+    by_plot = {g["plot_number"]: g["owner_id"] for g in graves}
+    assert by_plot["1"] == aftab["id"] and by_plot["2"] == aftab["id"], by_plot
+    assert by_plot["5"] == aftab["id"], by_plot
+    assert by_plot["4"] is None and by_plot["6"] is None and by_plot["7"] is None, by_plot
+    assert "owner_name" not in cols and "owner_contact" not in cols, cols
 
 
 if __name__ == "__main__":

```