# Review package: task-3

No git in this project: this diff is snapshot-to-snapshot,
base `task-3-base` -> current working tree.

## Files changed

- graveyard/api.py
- tests/test_owners.py

## Stat

2 files, +144 / -0 lines

## Full diff

```diff
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-3-base/graveyard/api.py C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-3-head/graveyard/api.py
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-3-base/graveyard/api.py	2026-09-20 18:42:59.517944100 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-3-head/graveyard/api.py	2026-09-21 08:42:14.152513400 -0400
@@ -43,6 +43,8 @@
         return "A section with that code already exists."
     if "FOREIGN KEY constraint failed" in message:
         return "The selected section no longer exists. Reopen the form and choose a section."
+    if "owners.name" in message:
+        return "An owner with that name already exists."
     return message
 
 
@@ -158,6 +160,77 @@
         documents.discard(doomed)
         return True
 
+    # ----- Owners ---------------------------------------------------------
+    @_endpoint
+    def list_owners(self, search: str = "") -> list[dict]:
+        clauses, params = [], []
+        if search.strip():
+            term = f"%{search.strip()}%"
+            clauses.append("(o.name LIKE ? OR o.contact LIKE ?)")
+            params.extend([term, term])
+        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
+        with get_connection() as conn:
+            return _rows(conn.execute(
+                f"""SELECT o.*, (SELECT COUNT(*) FROM graves g WHERE g.owner_id = o.id)
+                           AS grave_count
+                    FROM owners o {where} ORDER BY o.name""", params))
+
+    @_endpoint
+    def get_owner(self, owner_id: int) -> dict:
+        with get_connection() as conn:
+            owner = conn.execute("SELECT * FROM owners WHERE id = ?", (owner_id,)).fetchone()
+            if owner is None:
+                raise ValueError("Owner not found.")
+            graves = _rows(conn.execute(
+                """SELECT g.id, g.plot_number, g.status, s.code AS section_code
+                   FROM graves g JOIN sections s ON s.id = g.section_id
+                   WHERE g.owner_id = ? ORDER BY s.code, g.plot_number""", (owner_id,)))
+        result = dict(owner)
+        result["graves"] = graves
+        return result
+
+    @_endpoint
+    def create_owner(self, name: str, contact: str = "", address: str = "",
+                     notes: str = "") -> int:
+        name = name.strip()
+        if not name:
+            raise ValueError("Owner name is required.")
+        with get_connection() as conn:
+            cur = conn.execute(
+                "INSERT INTO owners (name, contact, address, notes) VALUES (?, ?, ?, ?)",
+                (name, contact.strip(), address.strip(), notes.strip()))
+            return cur.lastrowid
+
+    @_endpoint
+    def update_owner(self, owner_id: int, name: str, contact: str = "",
+                     address: str = "", notes: str = "") -> bool:
+        name = name.strip()
+        if not name:
+            raise ValueError("Owner name is required.")
+        with get_connection() as conn:
+            conn.execute(
+                """UPDATE owners SET name = ?, contact = ?, address = ?, notes = ?,
+                   updated_at = datetime('now') WHERE id = ?""",
+                (name, contact.strip(), address.strip(), notes.strip(), owner_id))
+        return True
+
+    @_endpoint
+    def delete_owner(self, owner_id: int) -> bool:
+        with get_connection() as conn:
+            owner = conn.execute(
+                "SELECT name FROM owners WHERE id = ?", (owner_id,)).fetchone()
+            if owner is None:
+                raise ValueError("Owner not found.")
+            held = conn.execute(
+                "SELECT COUNT(*) c FROM graves WHERE owner_id = ?", (owner_id,)
+            ).fetchone()["c"]
+            if held:
+                raise ValueError(
+                    f"{owner['name']} still holds {held} "
+                    f"plot{'' if held == 1 else 's'}. Reassign them first.")
+            conn.execute("DELETE FROM owners WHERE id = ?", (owner_id,))
+        return True
+
     # ----- Graves ---------------------------------------------------------
     @_endpoint
     def list_graves(self, section_id=None, status=None, search="") -> list[dict]:
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-3-base/tests/test_owners.py C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-3-head/tests/test_owners.py
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-3-base/tests/test_owners.py	2026-09-21 08:37:16.834245700 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-3-head/tests/test_owners.py	2026-09-21 08:43:33.441798600 -0400
@@ -3,6 +3,7 @@
 Run: python tests/test_owners.py
 """
 
+import gc
 import os
 import shutil
 import sqlite3
@@ -17,6 +18,7 @@
 DB = TMP / "test.db"
 os.environ["GRAVEYARD_DB"] = str(DB)
 
+from graveyard.api import Api  # noqa: E402
 from graveyard.database import get_connection, init_db  # noqa: E402
 
 PASS, FAIL = [], []
@@ -55,6 +57,20 @@
     return res["data"]
 
 
+def err(res):
+    assert not res["ok"], f"expected failure, got: {res.get('data')}"
+    return res["error"]
+
+
+def _fresh():
+    """Delete the DB, reinitialize with current schema, and return Api()."""
+    gc.collect()  # Force garbage collection to release file handles on Windows
+    if DB.exists():
+        DB.unlink()
+    init_db()
+    return Api()
+
+
 def _build_old_db():
     """A pre-owners database exercising every "no owner" and dedupe path:
     a duplicate name with two contacts, a whitespace-padded duplicate of
@@ -193,6 +209,61 @@
     assert "owner_name" not in cols and "owner_contact" not in cols, cols
 
 
+def t_owner_crud_round_trip():
+    a = _fresh()
+    oid = ok(a.create_owner("Aftab Dar", "222-444-777", "1 Main St", "prefers email"))
+    o = ok(a.get_owner(oid))
+    assert o["name"] == "Aftab Dar" and o["contact"] == "222-444-777", o
+    assert o["address"] == "1 Main St" and o["graves"] == [], o
+    ok(a.update_owner(oid, "Aftab Dar", "222-444-7777", "2 Main St", ""))
+    assert ok(a.get_owner(oid))["contact"] == "222-444-7777"
+    ok(a.delete_owner(oid))
+    assert ok(a.list_owners()) == []
+
+
+def t_owner_name_must_be_unique():
+    a = _fresh()
+    ok(a.create_owner("Aftab Dar"))
+    msg = err(a.create_owner("Aftab Dar"))
+    assert "already" in msg.lower(), msg
+
+
+def t_owner_name_required():
+    a = _fresh()
+    err(a.create_owner("   "))
+
+
+def t_delete_owner_blocked_while_holding_graves():
+    a = _fresh()
+    sid = ok(a.create_section("A", "Garden"))
+    oid = ok(a.create_owner("Aftab Dar"))
+    ok(a.create_grave(sid, "1", "available", oid))
+    msg = err(a.delete_owner(oid))
+    assert "Aftab Dar" in msg and "1 plot" in msg, msg
+    assert len(ok(a.list_owners())) == 1, "owner must survive a refused delete"
+
+
+def t_delete_owner_allowed_once_empty():
+    a = _fresh()
+    sid = ok(a.create_section("A", "Garden"))
+    oid = ok(a.create_owner("Aftab Dar"))
+    gid = ok(a.create_grave(sid, "1", "available", oid))
+    ok(a.delete_grave(gid))
+    ok(a.delete_owner(oid))
+
+
+def t_list_owners_reports_grave_count_and_search():
+    a = _fresh()
+    sid = ok(a.create_section("A", "Garden"))
+    oid = ok(a.create_owner("Aftab Dar", "222-444-777"))
+    ok(a.create_owner("Margaret Whitfield", "555-0142"))
+    ok(a.create_grave(sid, "1", "available", oid))
+    ok(a.create_grave(sid, "2", "available", oid))
+    rows = {o["name"]: o["grave_count"] for o in ok(a.list_owners())}
+    assert rows == {"Aftab Dar": 2, "Margaret Whitfield": 0}, rows
+    assert [o["name"] for o in ok(a.list_owners("whitfield"))] == ["Margaret Whitfield"]
+
+
 if __name__ == "__main__":
     for name, fn in sorted(globals().items()):
         if name.startswith("t_"):

```