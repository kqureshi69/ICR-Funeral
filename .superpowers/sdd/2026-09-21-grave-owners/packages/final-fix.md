# Review package: final-fix

No git in this project: this diff is snapshot-to-snapshot,
base `final-fix-base` -> current working tree.

## Files changed

- docs/superpowers/plans/2026-09-21-grave-owners.md
- docs/superpowers/specs/2026-09-21-grave-owners-design.md
- graveyard/api.py
- graveyard/seed.py
- graveyard/web/js/app.js
- tests/test_owners.py

## Stat

6 files, +80 / -24 lines

## Full diff

```diff
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-base/docs/superpowers/plans/2026-09-21-grave-owners.md C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-head/docs/superpowers/plans/2026-09-21-grave-owners.md
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-base/docs/superpowers/plans/2026-09-21-grave-owners.md	2026-09-21 08:17:29.582391500 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-head/docs/superpowers/plans/2026-09-21-grave-owners.md	2026-09-21 15:33:34.092712000 -0400
@@ -960,7 +960,7 @@
 - Consumes: everything above.
 - Produces: a migrated live database and current documentation.
 
-- [ ] **Step 1: Back up the live database**
+- [x] **Step 1: Back up the live database**
 
 ```bash
 cd /c/ClaudeCode/funeral
@@ -968,7 +968,7 @@
 ls -la data/*.db
 ```
 
-- [ ] **Step 2: Run the migration**
+- [x] **Step 2: Run the migration**
 
 ```bash
 .venv/Scripts/python.exe -c "
@@ -985,11 +985,11 @@
 "
 ```
 
-Expected: `owner_name` and `owner_contact` absent from `graves`; **9 owners**; `Aftab Dar` with contact `222-444-777` holding 2 plots; `unassigned: 3`.
+Expected: `owner_name` and `owner_contact` absent from `graves`; **9 owners**; `Aftab Dar` with contact `222-555-7777` holding 2 plots; `unassigned: 3`.
 
 If the counts differ, stop and restore from the Step 1 backup before investigating.
 
-- [ ] **Step 3: Update the README**
+- [x] **Step 3: Update the README**
 
 - Features: change the Graves bullet so ownership reads as a linked owner record, and add an Owners bullet.
 - Architecture tree: add `js/` files from Task 1 and `tests/test_owners.py`.
@@ -997,12 +997,12 @@
 - Migrations section: note that `init_db()` also runs `_migrate_owners`, which is one-way and drops columns.
 - Tests section: add `python tests/test_owners.py`.
 
-- [ ] **Step 4: Final checkpoint**
+- [x] **Step 4: Final checkpoint**
 
 Run all three Python suites and every live check (visibility, first-run flow, documents UI, owners). Confirm the app opens against the real migrated database with all plots listed and owners populated.
 
-- [ ] **Step 5: Report the two known manual follow-ups**
+- [x] **Step 5: Report the two known manual follow-ups**
 
 Tell the project owner explicitly:
 1. `Estate of John Whitfield` and `Estate of John Whitfield - 2` are two separate owners; repoint the second plot and delete the spare.
-2. `Aftab Dar`'s discarded contact `222-555-7777` is gone from the live data but present in the Step 1 backup if it was the correct number.
+2. `Aftab Dar`'s discarded contact `222-444-777` is gone from the live data but present in the Step 1 backup if it was the correct number.
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-base/docs/superpowers/specs/2026-09-21-grave-owners-design.md C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-head/docs/superpowers/specs/2026-09-21-grave-owners-design.md
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-base/docs/superpowers/specs/2026-09-21-grave-owners-design.md	2026-09-21 08:09:16.413955200 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-head/docs/superpowers/specs/2026-09-21-grave-owners-design.md	2026-09-21 15:33:14.764293900 -0400
@@ -25,7 +25,9 @@
 1. **One owner per grave.** An owner holds many graves. Joint ownership is
    expressed by naming the estate or family, as the existing data already does.
 2. **Duplicate merge keeps the first contact.** `Aftab Dar` becomes one owner
-   with `222-444-777`; `222-555-7777` is discarded.
+   with `222-555-7777`; `222-444-777` is discarded (the discarded value is
+   nine digits and appears to be a typo, while the surviving one is well
+   formed).
 3. **Owners get their own view**, as a sidebar tab beside Sections, plus inline
    creation from the grave form.
 4. **Owner name is unique.** This is the constraint that prevents the duplicate
@@ -140,7 +142,7 @@
 migration begins so an old runtime fails loudly rather than halfway through.
 
 **Expected result on the live database:** 9 owners; `Aftab Dar` merged onto
-`222-444-777`; 3 graves left unassigned. `Estate of John Whitfield` and
+`222-555-7777`; 3 graves left unassigned. `Estate of John Whitfield` and
 `Estate of John Whitfield - 2` remain two owners — the migration cannot know they
 are the same estate, and merging them is a manual follow-up the new UI enables.
 
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-base/graveyard/api.py C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-head/graveyard/api.py
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-base/graveyard/api.py	2026-09-21 08:50:23.567438400 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-head/graveyard/api.py	2026-09-21 15:31:32.749161600 -0400
@@ -60,6 +60,19 @@
         raise ValueError("The selected section no longer exists. Reopen the form and choose a section.")
 
 
+def _require_grave_owner(conn, owner_id) -> None:
+    """No-op when owner_id is empty; raise a clear error if it's set but stale.
+
+    This is unrelated to ``_require_owner`` below, which validates the parent
+    record a *document* attaches to (a section, grave or burial). This one
+    validates the ``owners`` row a *grave* points to.
+    """
+    if not owner_id:
+        return
+    if conn.execute("SELECT 1 FROM owners WHERE id = ?", (owner_id,)).fetchone() is None:
+        raise ValueError("The selected owner no longer exists. Reopen the form and choose an owner.")
+
+
 # A document hangs off exactly one of these; the table's CHECK enforces it.
 OWNER_COLUMNS = {"section": "section_id", "grave": "grave_id", "burial": "burial_id"}
 OWNER_TABLES = {"section": "sections", "grave": "graves", "burial": "burials"}
@@ -311,6 +324,7 @@
             raise ValueError("Plot number is required.")
         with get_connection() as conn:
             _require_section(conn, section_id)
+            _require_grave_owner(conn, owner_id)
             cur = conn.execute(
                 """INSERT INTO graves
                    (section_id, plot_number, status, owner_id,
@@ -329,6 +343,7 @@
             raise ValueError("Plot number is required.")
         with get_connection() as conn:
             _require_section(conn, section_id)
+            _require_grave_owner(conn, owner_id)
             conn.execute(
                 """UPDATE graves
                    SET section_id = ?, plot_number = ?, status = ?,
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-base/graveyard/seed.py C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-head/graveyard/seed.py
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-base/graveyard/seed.py	2026-09-20 17:14:00.694652500 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-head/graveyard/seed.py	2026-09-21 15:32:09.754562100 -0400
@@ -16,17 +16,27 @@
     ("C", "Veterans Field", "Reserved for service members and spouses."),
 ]
 
-# (section_code, plot_number, status, owner_name, owner_contact, notes)
+# (name, contact)
+OWNERS = [
+    ("Estate of John Whitfield", "—"),
+    ("Estate of John Whitfield - 2", "—"),
+    ("Margaret Whitfield", "555-0142"),
+    ("Acosta Family", "acosta.fam@example.com"),
+    ("Daniel Okoro", "555-0199"),
+    ("Sgt. Harold Bain (ret.)", "next-of-kin: 555-0177"),
+]
+
+# (section_code, plot_number, status, owner_name, notes)
 GRAVES = [
-    ("A", "1", "occupied", "Estate of John Whitfield", "—", "Family plot, 4 spaces."),
-    ("A", "2", "occupied", "Estate of John Whitfield", "—", ""),
-    ("A", "3", "reserved", "Margaret Whitfield", "555-0142", "Pre-purchased 2019."),
-    ("A", "4", "available", "", "", ""),
-    ("B", "10", "occupied", "Acosta Family", "acosta.fam@example.com", ""),
-    ("B", "11", "available", "", "", ""),
-    ("B", "12", "reserved", "Daniel Okoro", "555-0199", ""),
-    ("C", "V-1", "occupied", "Sgt. Harold Bain (ret.)", "next-of-kin: 555-0177", "Flag holder installed."),
-    ("C", "V-2", "available", "", "", ""),
+    ("A", "1", "occupied", "Estate of John Whitfield", "Family plot, 4 spaces."),
+    ("A", "2", "occupied", "Estate of John Whitfield - 2", ""),
+    ("A", "3", "reserved", "Margaret Whitfield", "Pre-purchased 2019."),
+    ("A", "4", "available", None, ""),
+    ("B", "10", "occupied", "Acosta Family", ""),
+    ("B", "11", "available", None, ""),
+    ("B", "12", "reserved", "Daniel Okoro", ""),
+    ("C", "V-1", "occupied", "Sgt. Harold Bain (ret.)", "Flag holder installed."),
+    ("C", "V-2", "available", None, ""),
 ]
 
 # (section_code, plot_number, deceased_name, date_of_death, date_of_burial, notes)
@@ -47,7 +57,7 @@
                 "SELECT stored_name FROM documents")]
             conn.executescript(
                 "DELETE FROM documents; DELETE FROM burials; "
-                "DELETE FROM graves; DELETE FROM sections;"
+                "DELETE FROM graves; DELETE FROM owners; DELETE FROM sections;"
             )
             documents.discard(stored)
 
@@ -61,13 +71,24 @@
                 "SELECT id FROM sections WHERE code = ?", (code,)
             ).fetchone()["id"]
 
+        owner_ids: dict[str, int] = {}
+        for name, contact in OWNERS:
+            cur = conn.execute(
+                "INSERT OR IGNORE INTO owners (name, contact) VALUES (?, ?)",
+                (name, contact),
+            )
+            owner_ids[name] = cur.lastrowid or conn.execute(
+                "SELECT id FROM owners WHERE name = ?", (name,)
+            ).fetchone()["id"]
+
         grave_ids: dict[tuple[str, str], int] = {}
-        for code, plot, status, owner, contact, notes in GRAVES:
+        for code, plot, status, owner, notes in GRAVES:
+            owner_id = owner_ids[owner] if owner else None
             cur = conn.execute(
                 """INSERT OR IGNORE INTO graves
-                   (section_id, plot_number, status, owner_name, owner_contact, notes)
-                   VALUES (?, ?, ?, ?, ?, ?)""",
-                (section_ids[code], plot, status, owner, contact, notes),
+                   (section_id, plot_number, status, owner_id, notes)
+                   VALUES (?, ?, ?, ?, ?)""",
+                (section_ids[code], plot, status, owner_id, notes),
             )
             grave_ids[(code, plot)] = cur.lastrowid or conn.execute(
                 "SELECT id FROM graves WHERE section_id = ? AND plot_number = ?",
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-base/graveyard/web/js/app.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-head/graveyard/web/js/app.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-base/graveyard/web/js/app.js	2026-09-21 09:07:14.854268800 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-head/graveyard/web/js/app.js	2026-09-21 15:31:42.596678200 -0400
@@ -33,11 +33,13 @@
   if (t.dataset.onboardGrave !== undefined) { await openGraveModal(null); return; }
   if (t.dataset.clearFilters !== undefined) {
     state.sectionId = null;
+    state.ownerId = null;
     state.status = "";
     state.search = "";
     el("statusFilter").value = "";
     el("searchInput").value = "";
     await refreshSections();
+    await refreshOwners();
     await refreshGraves();
     return;
   }
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-base/tests/test_owners.py C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-head/tests/test_owners.py
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-base/tests/test_owners.py	2026-09-21 08:49:28.015961700 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-fix-head/tests/test_owners.py	2026-09-21 15:32:28.806599600 -0400
@@ -304,6 +304,22 @@
     assert len(found) == 1 and found[0]["plot_number"] == "1", found
 
 
+def t_update_grave_with_stale_owner_reports_owner_not_section():
+    a = _fresh()
+    sid = ok(a.create_section("A", "Garden"))
+    oid = ok(a.create_owner("Aftab Dar"))
+    gid = ok(a.create_grave(sid, "1", "available", oid))
+    # Bypass delete_owner's guard with a raw connection (foreign_keys stays
+    # OFF by default, unlike get_connection, so this delete isn't blocked).
+    raw = sqlite3.connect(DB)
+    raw.execute("DELETE FROM owners WHERE id = ?", (oid,))
+    raw.commit()
+    raw.close()
+    msg = err(a.update_grave(gid, sid, "1", "available", oid))
+    assert "owner" in msg.lower(), msg
+    assert "section" not in msg.lower(), msg
+
+
 if __name__ == "__main__":
     for name, fn in sorted(globals().items()):
         if name.startswith("t_"):

```