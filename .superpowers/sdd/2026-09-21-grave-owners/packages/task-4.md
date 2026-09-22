# Review package: task-4

No git in this project: this diff is snapshot-to-snapshot,
base `task-4-base` -> current working tree.

## Files changed

- graveyard/api.py
- tests/test_graves.py
- tests/test_owners.py

## Stat

3 files, +73 / -21 lines

## Full diff

```diff
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-4-base/graveyard/api.py C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-4-head/graveyard/api.py
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-4-base/graveyard/api.py	2026-09-21 08:42:14.152513400 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-4-head/graveyard/api.py	2026-09-21 08:50:23.567438400 -0400
@@ -96,6 +96,11 @@
     return column
 
 
+def _owner_or_none(owner_id):
+    """The dropdown sends "" for an unassigned owner; store NULL."""
+    return int(owner_id) if owner_id else None
+
+
 def _descendant_docs(conn, owner_type, owner_id) -> list[str]:
     _owner_column(owner_type)  # rejects an unknown owner type
     sql, repeats = _DESCENDANT_DOCS[owner_type]
@@ -233,7 +238,7 @@
 
     # ----- Graves ---------------------------------------------------------
     @_endpoint
-    def list_graves(self, section_id=None, status=None, search="") -> list[dict]:
+    def list_graves(self, section_id=None, status=None, search="", owner_id=None) -> list[dict]:
         clauses, params = [], []
         if section_id:
             clauses.append("g.section_id = ?")
@@ -241,10 +246,13 @@
         if status:
             clauses.append("g.status = ?")
             params.append(status)
+        if owner_id:
+            clauses.append("g.owner_id = ?")
+            params.append(owner_id)
         if search.strip():
             term = f"%{search.strip()}%"
-            clauses.append("(g.plot_number LIKE ? OR g.owner_name LIKE ?"
-                           " OR g.grave_ref LIKE ? OR g.deed_id LIKE ?)")
+            clauses.append("(g.plot_number LIKE ? OR g.grave_ref LIKE ?"
+                           " OR g.deed_id LIKE ? OR o.name LIKE ?)")
             params.extend([term, term, term, term])
         where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
         with get_connection() as conn:
@@ -252,10 +260,12 @@
                 conn.execute(
                     f"""
                     SELECT g.*, s.code AS section_code, s.name AS section_name,
+                           o.name AS owner_name, o.contact AS owner_contact,
                            (SELECT COUNT(*) FROM documents d
                              WHERE d.grave_id = g.id) AS doc_count
                     FROM graves g
                     JOIN sections s ON s.id = g.section_id
+                    LEFT JOIN owners o ON o.id = g.owner_id
                     {where}
                     ORDER BY s.code, g.plot_number
                     """,
@@ -269,9 +279,11 @@
             grave = conn.execute(
                 """
                 SELECT g.*, s.code AS section_code, s.name AS section_name,
+                       o.name AS owner_name, o.contact AS owner_contact,
                        (SELECT COUNT(*) FROM documents d
                          WHERE d.grave_id = g.id) AS doc_count
                 FROM graves g JOIN sections s ON s.id = g.section_id
+                LEFT JOIN owners o ON o.id = g.owner_id
                 WHERE g.id = ?
                 """,
                 (grave_id,),
@@ -293,27 +305,26 @@
 
     @_endpoint
     def create_grave(self, section_id, plot_number, status="available",
-                     owner_name="", owner_contact="", notes="",
-                     grave_ref="", deed_id="", date_purchased="") -> int:
+                     owner_id=None, notes="", grave_ref="", deed_id="",
+                     date_purchased="") -> int:
         if not str(plot_number).strip():
             raise ValueError("Plot number is required.")
         with get_connection() as conn:
             _require_section(conn, section_id)
             cur = conn.execute(
                 """INSERT INTO graves
-                   (section_id, plot_number, status, owner_name, owner_contact,
+                   (section_id, plot_number, status, owner_id,
                     notes, grave_ref, deed_id, date_purchased)
-                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
-                (section_id, str(plot_number).strip(), status,
-                 owner_name.strip(), owner_contact.strip(), notes.strip(),
-                 grave_ref.strip(), deed_id.strip(), date_purchased.strip()),
-            )
+                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
+                (section_id, str(plot_number).strip(), status, _owner_or_none(owner_id),
+                 notes.strip(), grave_ref.strip(), deed_id.strip(),
+                 date_purchased.strip()))
             return cur.lastrowid
 
     @_endpoint
     def update_grave(self, grave_id, section_id, plot_number, status,
-                     owner_name="", owner_contact="", notes="",
-                     grave_ref="", deed_id="", date_purchased="") -> bool:
+                     owner_id=None, notes="", grave_ref="", deed_id="",
+                     date_purchased="") -> bool:
         if not str(plot_number).strip():
             raise ValueError("Plot number is required.")
         with get_connection() as conn:
@@ -321,12 +332,12 @@
             conn.execute(
                 """UPDATE graves
                    SET section_id = ?, plot_number = ?, status = ?,
-                       owner_name = ?, owner_contact = ?, notes = ?,
+                       owner_id = ?, notes = ?,
                        grave_ref = ?, deed_id = ?, date_purchased = ?,
                        updated_at = datetime('now')
                    WHERE id = ?""",
                 (section_id, str(plot_number).strip(), status,
-                 owner_name.strip(), owner_contact.strip(), notes.strip(),
+                 _owner_or_none(owner_id), notes.strip(),
                  grave_ref.strip(), deed_id.strip(), date_purchased.strip(), grave_id),
             )
         return True
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-4-base/tests/test_graves.py C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-4-head/tests/test_graves.py
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-4-base/tests/test_graves.py	2026-09-20 18:42:09.049965500 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-4-head/tests/test_graves.py	2026-09-21 08:49:47.813275600 -0400
@@ -74,7 +74,8 @@
 
 def t_new_fields_round_trip():
     a, sid = fresh()
-    gid = ok(a.create_grave(sid, "1", "reserved", "M. Whitfield", "555-0142",
+    oid = ok(a.create_owner("M. Whitfield", "555-0142"))
+    gid = ok(a.create_grave(sid, "1", "reserved", oid,
                             "Family plot", "GRV-00412", "DEED-77", "2019-04-02"))
     g = ok(a.get_grave(gid))
     assert g["grave_ref"] == "GRV-00412", g
@@ -93,8 +94,8 @@
 def t_update_changes_new_fields():
     a, sid = fresh()
     gid = ok(a.create_grave(sid, "1"))
-    ok(a.update_grave(gid, sid, "1", "available", "", "", "",
-                      "GRV-9", "DEED-9", "2020-01-01"))
+    ok(a.update_grave(gid, sid, "1", "available", None,
+                      "", "GRV-9", "DEED-9", "2020-01-01"))
     g = ok(a.get_grave(gid))
     assert (g["grave_ref"], g["deed_id"], g["date_purchased"]) \
         == ("GRV-9", "DEED-9", "2020-01-01"), g
@@ -102,14 +103,14 @@
 
 def t_list_graves_exposes_new_fields():
     a, sid = fresh()
-    ok(a.create_grave(sid, "1", "available", "", "", "", "GRV-1", "D-1", "2021-06-01"))
+    ok(a.create_grave(sid, "1", "available", None, "", "GRV-1", "D-1", "2021-06-01"))
     row = ok(a.list_graves())[0]
     assert row["grave_ref"] == "GRV-1" and row["deed_id"] == "D-1", row
 
 
 def t_search_matches_grave_ref():
     a, sid = fresh()
-    ok(a.create_grave(sid, "1", "available", "", "", "", "GRV-00412", "", ""))
+    ok(a.create_grave(sid, "1", "available", None, "", "GRV-00412", "", ""))
     ok(a.create_grave(sid, "2"))
     found = ok(a.list_graves(None, "", "00412"))
     assert len(found) == 1 and found[0]["plot_number"] == "1", found
@@ -117,7 +118,7 @@
 
 def t_search_matches_deed_id():
     a, sid = fresh()
-    ok(a.create_grave(sid, "1", "available", "", "", "", "", "DEED-77", ""))
+    ok(a.create_grave(sid, "1", "available", None, "", "", "DEED-77", ""))
     ok(a.create_grave(sid, "2"))
     found = ok(a.list_graves(None, "", "DEED-77"))
     assert len(found) == 1 and found[0]["plot_number"] == "1", found
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-4-base/tests/test_owners.py C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-4-head/tests/test_owners.py
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-4-base/tests/test_owners.py	2026-09-21 08:43:33.441798600 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-4-head/tests/test_owners.py	2026-09-21 08:49:28.015961700 -0400
@@ -264,6 +264,46 @@
     assert [o["name"] for o in ok(a.list_owners("whitfield"))] == ["Margaret Whitfield"]
 
 
+def t_grave_stores_and_changes_owner():
+    a = _fresh()
+    sid = ok(a.create_section("A", "Garden"))
+    o1 = ok(a.create_owner("Aftab Dar", "222-444-777"))
+    o2 = ok(a.create_owner("Margaret Whitfield"))
+    gid = ok(a.create_grave(sid, "1", "available", o1))
+    g = ok(a.get_grave(gid))
+    assert g["owner_id"] == o1 and g["owner_name"] == "Aftab Dar", g
+    assert g["owner_contact"] == "222-444-777", g
+    ok(a.update_grave(gid, sid, "1", "available", o2))
+    assert ok(a.get_grave(gid))["owner_name"] == "Margaret Whitfield"
+
+
+def t_grave_owner_is_optional():
+    a = _fresh()
+    sid = ok(a.create_section("A", "Garden"))
+    gid = ok(a.create_grave(sid, "1"))
+    g = ok(a.get_grave(gid))
+    assert g["owner_id"] is None and g["owner_name"] is None, g
+
+
+def t_unowned_graves_still_listed():
+    """A LEFT JOIN regression guard: an inner join would hide this row."""
+    a = _fresh()
+    sid = ok(a.create_section("A", "Garden"))
+    ok(a.create_grave(sid, "1"))
+    assert len(ok(a.list_graves())) == 1, "unowned grave vanished from the list"
+
+
+def t_list_graves_filters_by_owner_and_searches_owner_name():
+    a = _fresh()
+    sid = ok(a.create_section("A", "Garden"))
+    oid = ok(a.create_owner("Aftab Dar"))
+    ok(a.create_grave(sid, "1", "available", oid))
+    ok(a.create_grave(sid, "2"))
+    assert len(ok(a.list_graves(None, "", "", oid))) == 1
+    found = ok(a.list_graves(None, "", "Aftab"))
+    assert len(found) == 1 and found[0]["plot_number"] == "1", found
+
+
 if __name__ == "__main__":
     for name, fn in sorted(globals().items()):
         if name.startswith("t_"):

```