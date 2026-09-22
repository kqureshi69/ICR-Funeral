# Review package: final

No git in this project: this diff is snapshot-to-snapshot,
base `task-1-base` -> current working tree.

## Files changed

- README.md
- graveyard/api.py
- graveyard/database.py
- graveyard/schema.sql
- graveyard/web/css/styles.css
- graveyard/web/index.html
- graveyard/web/js/api.js
- graveyard/web/js/app.js
- graveyard/web/js/documents.js
- graveyard/web/js/graves.js
- graveyard/web/js/owners.js
- graveyard/web/js/sections.js
- graveyard/web/js/state.js
- graveyard/web/js/util.js
- tests/test_graves.py
- tests/test_owners.py

## Stat

16 files, +1173 / -477 lines

## Full diff

```diff
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/README.md C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/README.md
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/README.md	2026-09-20 18:45:31.209489000 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/README.md	2026-09-21 15:23:58.486308400 -0400
@@ -13,7 +13,12 @@
 ## Features
 
 - **Sections** — create/edit cemetery sections (code, name, description) with live plot counts.
-- **Graves** — add/edit plots per section with a unique plot number, owner name & contact, notes, and reference details (grave id, deed id, date purchased).
+- **Graves** — add/edit plots per section with a unique plot number, an owner
+  linked from the owners list (or created inline), notes, and reference details
+  (grave id, deed id, date purchased).
+- **Owners** — first-class owner records (name, contact) with their own
+  Sections|Owners sidebar tab, so graves can be filtered by owner exactly as
+  they are by section; one owner can hold several plots.
 - **Status tracking** — every grave is `available`, `reserved`, or `occupied`, shown as colour badges.
 - **Mark as used** — recording a burial automatically flips the grave to *occupied*; a grave can hold multiple burial records over time.
 - **Filtering** — filter by section, status, and free-text search across plot number, owner, grave id and deed id.
@@ -32,15 +37,24 @@
 │   ├── api.py              # Api class — every method is callable from JS
 │   ├── database.py         # SQLite connection + schema init
 │   ├── documents.py        # document store: files on disk beside the database
-│   ├── schema.sql          # tables: sections, graves, burials, documents
+│   ├── schema.sql          # tables: sections, owners, graves, burials, documents
 │   ├── seed.py             # example data loader
 │   └── web/                # frontend (served from disk by pywebview)
 │       ├── index.html
 │       ├── css/styles.css
-│       └── js/app.js
+│       └── js/
+│           ├── util.js     # shared helpers
+│           ├── api.js      # thin wrapper over window.pywebview.api
+│           ├── state.js    # in-memory app state
+│           ├── sections.js # sections tab: list, form, filtering
+│           ├── owners.js   # owners tab: list, form, inline create
+│           ├── graves.js   # graves list/form, owner dropdown
+│           ├── documents.js # document attach/list/open
+│           └── app.js      # entry point: wires the above together
 ├── tests/
 │   ├── test_documents.py   # `python tests/test_documents.py`
-│   └── test_graves.py      # grave reference fields + schema migration
+│   ├── test_graves.py      # grave reference fields + schema migration
+│   └── test_owners.py      # owners CRUD + owners migration/merge
 └── data/
     ├── graveyard.db        # created at first run (git-ignored)
     └── documents/          # uploaded files, named by UUID (git-ignored)
@@ -65,7 +79,8 @@
 | Table      | Purpose                                   | Key columns |
 |------------|-------------------------------------------|-------------|
 | `sections` | Cemetery sections                         | `code` (unique), `name` |
-| `graves`   | Individual plots                          | `section_id`, `plot_number` (unique per section), `status`, `owner_name`, `owner_contact`, `grave_ref` (shown as "Grave id"), `deed_id`, `date_purchased` |
+| `owners`   | Grave owners                              | `name` (unique), `contact` |
+| `graves`   | Individual plots                          | `section_id`, `plot_number` (unique per section), `status`, `owner_id` (nullable, `LEFT JOIN owners`), `grave_ref` (shown as "Grave id"), `deed_id`, `date_purchased` |
 | `burials`  | Burial records (a grave may have several) | `grave_id`, `deceased_name`, `date_of_death`, `date_of_burial` |
 | `documents`| Uploaded files, owned by exactly one record | `section_id` / `grave_id` / `burial_id` (exactly one set, enforced by `CHECK`), `original_name`, `stored_name` |
 
@@ -116,6 +131,14 @@
   missing from an existing database is added with `ALTER TABLE`. This is
   idempotent and preserves existing rows — adding a future column means adding
   one line to that dict.
+- **Owner migration**: `init_db()` also runs `_migrate_owners`, which folds any
+  existing `graves.owner_name` / `owner_contact` text into first-class `owners`
+  rows (deduplicating by trimmed name, first contact wins by lowest
+  `graves.id`) before dropping those two columns from `graves`. This step is
+  **one-way** — the dropped columns cannot be recovered from the database
+  afterwards — and self-heals if interrupted: it checks what's already been
+  migrated on each `init_db()` call, so re-running it on a database it's
+  already touched is a no-op.
 - **Seed** with `python -m graveyard.seed` (idempotent inserts) or
   `python -m graveyard.seed --reset` to clear all tables first.
 
@@ -126,6 +149,7 @@
 ```powershell
 python tests/test_documents.py    # plain asserts, no test framework needed
 python tests/test_graves.py
+python tests/test_owners.py
 ```
 
 `test_documents.py` covers the document store: attach/list/remove, cascade
@@ -136,6 +160,11 @@
 migration: it builds a database with the pre-release `graves` shape, runs
 `init_db()`, and asserts the new columns appear with existing rows intact.
 
+`test_owners.py` covers owner CRUD, grave endpoints filtering/writing by
+`owner_id`, and the `_migrate_owners` step itself: deduplication by trimmed
+name, the first-contact-wins tiebreak, and that `owner_name` / `owner_contact`
+are gone from `graves` afterwards.
+
 ## Packaging / deploy
 
 For a standalone executable, build with PyInstaller and include the `web/` assets:
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/api.py C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/api.py
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/api.py	2026-09-20 18:42:59.517944100 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/api.py	2026-09-21 08:50:23.567438400 -0400
@@ -43,6 +43,8 @@
         return "A section with that code already exists."
     if "FOREIGN KEY constraint failed" in message:
         return "The selected section no longer exists. Reopen the form and choose a section."
+    if "owners.name" in message:
+        return "An owner with that name already exists."
     return message
 
 
@@ -94,6 +96,11 @@
     return column
 
 
+def _owner_or_none(owner_id):
+    """The dropdown sends "" for an unassigned owner; store NULL."""
+    return int(owner_id) if owner_id else None
+
+
 def _descendant_docs(conn, owner_type, owner_id) -> list[str]:
     _owner_column(owner_type)  # rejects an unknown owner type
     sql, repeats = _DESCENDANT_DOCS[owner_type]
@@ -158,9 +165,80 @@
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
-    def list_graves(self, section_id=None, status=None, search="") -> list[dict]:
+    def list_graves(self, section_id=None, status=None, search="", owner_id=None) -> list[dict]:
         clauses, params = [], []
         if section_id:
             clauses.append("g.section_id = ?")
@@ -168,10 +246,13 @@
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
@@ -179,10 +260,12 @@
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
@@ -196,9 +279,11 @@
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
@@ -220,27 +305,26 @@
 
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
@@ -248,12 +332,12 @@
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
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/database.py C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/database.py
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/database.py	2026-09-20 18:42:43.457781600 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/database.py	2026-09-21 08:36:22.172210600 -0400
@@ -57,9 +57,77 @@
                 conn.execute(f"ALTER TABLE {table} ADD COLUMN {name} {spec}")
 
 
+def _migrate_owners(conn) -> None:
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
+    cols = {r["name"] for r in conn.execute("PRAGMA table_info(graves)")}
+    if not cols or "owner_name" not in cols:
+        return  # graves not created yet, or migration already committed
+
+    if tuple(map(int, sqlite3.sqlite_version.split("."))) < (3, 35, 0):
+        raise RuntimeError(
+            f"SQLite {sqlite3.sqlite_version} cannot DROP COLUMN; 3.35+ required."
+        )
+
+    if "owner_id" not in cols:
+        conn.execute("ALTER TABLE graves ADD COLUMN owner_id INTEGER REFERENCES owners(id)")
+
+    # SQLite guarantees bare columns in a MIN() aggregate come from the matching
+    # row, so `contact` here is the one from the lowest-id grave: first wins.
+    duplicates = conn.execute(
+        """SELECT TRIM(owner_name) AS name, owner_contact AS contact, MIN(id)
+           FROM graves
+           WHERE TRIM(COALESCE(owner_name, '')) <> ''
+           GROUP BY TRIM(owner_name)"""
+    ).fetchall()
+
+    for row in duplicates:
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
+        conn.execute(
+            "UPDATE graves SET owner_id = ? WHERE TRIM(owner_name) = ?",
+            (owner_id, row["name"]),
+        )
+
+    conn.execute("ALTER TABLE graves DROP COLUMN owner_name")
+    conn.execute("ALTER TABLE graves DROP COLUMN owner_contact")
+
+
+def _ensure_indexes(conn) -> None:
+    """Indexes that cannot live in schema.sql because they postdate a column."""
+    cols = {r["name"] for r in conn.execute("PRAGMA table_info(graves)")}
+    if "owner_id" in cols:
+        conn.execute("CREATE INDEX IF NOT EXISTS idx_graves_owner ON graves(owner_id)")
+
+
 def init_db() -> None:
     """Create tables from schema.sql if absent, then bring them up to date."""
     schema = SCHEMA_PATH.read_text(encoding="utf-8")
     with get_connection() as conn:
         conn.executescript(schema)
         _apply_migrations(conn)
+        _migrate_owners(conn)
+        _ensure_indexes(conn)
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/schema.sql C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/schema.sql
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/schema.sql	2026-09-20 18:42:43.557747000 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/schema.sql	2026-09-21 08:26:48.088123300 -0400
@@ -10,6 +10,18 @@
     created_at  TEXT NOT NULL DEFAULT (datetime('now'))
 );
 
+-- Plot owners. A grave is filed under exactly one owner (or none).
+CREATE TABLE IF NOT EXISTS owners (
+    id         INTEGER PRIMARY KEY AUTOINCREMENT,
+    name       TEXT NOT NULL,
+    contact    TEXT NOT NULL DEFAULT '',
+    address    TEXT NOT NULL DEFAULT '',
+    notes      TEXT NOT NULL DEFAULT '',
+    created_at TEXT NOT NULL DEFAULT (datetime('now')),
+    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
+);
+CREATE UNIQUE INDEX IF NOT EXISTS idx_owners_name ON owners(name);
+
 -- Individual grave plots. A plot number is unique within its section.
 CREATE TABLE IF NOT EXISTS graves (
     id            INTEGER PRIMARY KEY AUTOINCREMENT,
@@ -17,8 +29,7 @@
     plot_number   TEXT NOT NULL,
     status        TEXT NOT NULL DEFAULT 'available'
                   CHECK (status IN ('available', 'reserved', 'occupied')),
-    owner_name    TEXT,
-    owner_contact TEXT,
+    owner_id      INTEGER REFERENCES owners(id),
     notes         TEXT,
     grave_ref      TEXT NOT NULL DEFAULT '',   -- shown as "Grave id"
     deed_id        TEXT NOT NULL DEFAULT '',
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/css/styles.css C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/css/styles.css
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/css/styles.css	2026-09-20 18:43:18.709844300 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/css/styles.css	2026-09-21 08:55:40.801147600 -0400
@@ -53,6 +53,14 @@
 }
 .sidebar-head { display: flex; justify-content: space-between; align-items: center; }
 .sidebar-head h2 { font-size: 14px; text-transform: uppercase; color: var(--muted); margin: 0; }
+.tabs { display: flex; gap: 4px; }
+.tab {
+  font: inherit; font-size: 12px; text-transform: uppercase;
+  padding: 4px 8px; border: none; border-radius: 6px;
+  background: none; color: var(--muted); cursor: pointer;
+}
+.tab.active { background: #e7f0eb; color: var(--accent); font-weight: 600; }
+.modal-actions .spacer { flex: 1; }
 .section-list { list-style: none; margin: 14px 0 0; padding: 0; }
 .section-list li {
   padding: 10px 12px;
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/index.html C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/index.html
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/index.html	2026-09-20 18:43:30.720909800 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/index.html	2026-09-21 09:01:57.455649500 -0400
@@ -16,10 +16,15 @@
     <!-- Sidebar: sections -->
     <aside class="sidebar">
       <div class="sidebar-head">
-        <h2>Sections</h2>
+        <div class="tabs">
+          <button class="tab active" data-tab="sections">Sections</button>
+          <button class="tab" data-tab="owners">Owners</button>
+        </div>
         <button class="btn small" id="addSectionBtn">+ Add</button>
+        <button class="btn small" id="addOwnerBtn" hidden>+ Add</button>
       </div>
       <ul class="section-list" id="sectionList"></ul>
+      <ul class="section-list" id="ownerList" hidden></ul>
     </aside>
 
     <!-- Main: graves -->
@@ -43,7 +48,6 @@
             <th>Plot #</th>
             <th>Status</th>
             <th>Owner</th>
-            <th>Contact</th>
             <th class="actions-col">Actions</th>
           </tr>
         </thead>
@@ -72,11 +76,8 @@
             <option value="occupied">Occupied</option>
           </select>
         </label>
-        <label>Owner name
-          <input type="text" id="graveOwner" />
-        </label>
-        <label>Owner contact
-          <input type="text" id="graveContact" />
+        <label>Owner
+          <select id="graveOwnerSelect"></select>
         </label>
         <div class="field-row">
           <label>Grave id
@@ -172,8 +173,42 @@
     </div>
   </div>
 
+  <div class="modal-backdrop" id="ownerModal" hidden>
+    <div class="modal">
+      <h3 id="ownerModalTitle">Add Owner</h3>
+      <form id="ownerForm">
+        <input type="hidden" id="ownerId" />
+        <label>Name
+          <input type="text" id="ownerName" required placeholder="e.g. Aftab Dar" />
+        </label>
+        <label>Contact
+          <input type="text" id="ownerContact" placeholder="phone or email" />
+        </label>
+        <label>Address
+          <input type="text" id="ownerAddress" />
+        </label>
+        <label>Notes
+          <textarea id="ownerNotes" rows="4"></textarea>
+        </label>
+        <div class="modal-actions">
+          <button type="button" class="btn danger" id="deleteOwnerBtn" hidden>Delete</button>
+          <span class="spacer"></span>
+          <button type="button" class="btn" data-close>Cancel</button>
+          <button type="submit" class="btn primary">Save</button>
+        </div>
+      </form>
+    </div>
+  </div>
+
   <div class="toast" id="toast" hidden></div>
 
+  <script src="js/util.js"></script>
+  <script src="js/api.js"></script>
+  <script src="js/state.js"></script>
+  <script src="js/sections.js"></script>
+  <script src="js/owners.js"></script>
+  <script src="js/graves.js"></script>
+  <script src="js/documents.js"></script>
   <script src="js/app.js"></script>
 </body>
 </html>
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/api.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/api.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/api.js	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/api.js	2026-09-21 08:21:36.371682500 -0400
@@ -0,0 +1,12 @@
+"use strict";
+
+/* Thin wrapper around the Python API that unwraps the {ok, data|error}
+ * envelope and surfaces errors as a toast. */
+async function call(method, ...args) {
+  const res = await window.pywebview.api[method](...args);
+  if (!res.ok) {
+    toast(res.error, true);
+    throw new Error(res.error);
+  }
+  return res.data;
+}
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/app.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/app.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/app.js	2026-09-20 18:43:30.603695000 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/app.js	2026-09-21 09:07:14.854268800 -0400
@@ -1,442 +1,153 @@
-"use strict";
-
-/* Thin wrapper around the Python API that unwraps the {ok, data|error}
- * envelope and surfaces errors as a toast. */
-async function call(method, ...args) {
-  const res = await window.pywebview.api[method](...args);
-  if (!res.ok) {
-    toast(res.error, true);
-    throw new Error(res.error);
-  }
-  return res.data;
-}
-
-const $ = (sel) => document.querySelector(sel);
-const el = (id) => document.getElementById(id);
-
-let state = { sectionId: null, status: "", search: "", sections: [], totalGraves: 0,
-              docOwner: { type: null, id: null, title: "" } };
-
-/* ---------- Rendering ---------- */
-
-async function refreshStats() {
-  const s = await call("stats");
-  // Remembered so the empty state can tell "nothing recorded yet" apart from
-  // "records exist but the filters hide them".
-  state.totalGraves = s.total;
-  el("stats").innerHTML = `
-    <div><b>${s.total}</b>Total plots</div>
-    <div><b>${s.available}</b>Available</div>
-    <div><b>${s.reserved}</b>Reserved</div>
-    <div><b>${s.occupied}</b>Occupied</div>
-    <div><b>${s.sections}</b>Sections</div>`;
-}
-
-async function refreshSections() {
-  state.sections = await call("list_sections");
-  const list = el("sectionList");
-  const all = `<li class="${state.sectionId === null ? "active" : ""}" data-id="">
-      <div class="sec-name">All sections</div>
-      <div class="sec-meta"><span>Show every plot</span></div></li>`;
-  list.innerHTML = all + state.sections.map((s) => `
-    <li class="${state.sectionId === s.id ? "active" : ""}" data-id="${s.id}">
-      <button class="btn link sec-edit" data-edit-section="${s.id}">edit</button>
-      <button class="btn link sec-edit" data-docs-section="${s.id}">docs${docBadge(s.doc_count)}</button>
-      <div class="sec-name">${esc(s.code)} · ${esc(s.name)}</div>
-      <div class="sec-meta">
-        <span>${s.total_plots} plots</span>
-        <span>${s.available_plots || 0} free</span>
-      </div>
-    </li>`).join("");
-}
-
-async function refreshGraves() {
-  const graves = await call("list_graves", state.sectionId, state.status, state.search);
-  const body = el("graveBody");
-  body.innerHTML = graves.map((g) => `
-    <tr>
-      <td>${esc(g.section_code)}</td>
-      <td>${esc(g.plot_number)}</td>
-      <td><span class="badge ${g.status}">${g.status}</span></td>
-      <td>${esc(g.owner_name || "—")}</td>
-      <td>${esc(g.owner_contact || "—")}</td>
-      <td class="actions-col">
-        <button class="btn link" data-docs-grave="${g.id}">Docs${docBadge(g.doc_count)}</button>
-        <button class="btn link" data-detail="${g.id}">Burials</button>
-        <button class="btn link" data-edit="${g.id}">Edit</button>
-        <button class="btn link danger" data-del="${g.id}">Delete</button>
-      </td>
-    </tr>`).join("");
-  renderEmptyState(graves.length);
-}
-
-/* An empty table means one of three different things. Saying which one, and
- * offering the action that resolves it, is the difference between a dead end
- * and a next step. */
-function renderEmptyState(graveCount) {
-  const firstRun = state.sections.length === 0;
-  const box = el("emptyState");
-
-  // On first run there is nothing to search, filter or list yet.
-  el("toolbar").hidden = firstRun;
-  el("graveTable").hidden = firstRun || graveCount === 0;
-
-  if (firstRun) {
-    box.innerHTML = `
-      <h2>Welcome to Grave Inventory</h2>
-      <p>Plots belong to a section, so start by creating one &mdash; for example
-         <b>A &middot; Garden of Peace</b>. You can add plots to it straight after.</p>
-      <button class="btn primary" data-onboard-section>Create first section</button>`;
-  } else if (graveCount > 0) {
-    box.hidden = true;
-    return;
-  } else if (state.totalGraves > 0) {
-    box.innerHTML = `
-      <p>No graves match the current filters.</p>
-      <button class="btn" data-clear-filters>Clear filters</button>`;
-  } else {
-    box.innerHTML = `
-      <p>No plots recorded yet.</p>
-      <button class="btn primary" data-onboard-grave>Add the first grave</button>`;
-  }
-  box.hidden = false;
-}
-
-async function refreshAll() {
-  // Sections must land before graves: the empty state can only choose its
-  // message once it knows whether any section exists.
-  await Promise.all([refreshStats(), refreshSections()]);
-  await refreshGraves();
-}
-
-/* ---------- Section modal ---------- */
-
-function openSectionModal(section) {
-  el("sectionModalTitle").textContent = section ? "Edit Section" : "Add Section";
-  el("sectionId").value = section ? section.id : "";
-  el("sectionCode").value = section ? section.code : "";
-  el("sectionName").value = section ? section.name : "";
-  el("sectionDesc").value = section ? section.description || "" : "";
-  show("sectionModal");
-}
-
-el("sectionForm").addEventListener("submit", async (e) => {
-  e.preventDefault();
-  const id = el("sectionId").value;
-  const args = [el("sectionCode").value, el("sectionName").value, el("sectionDesc").value];
-  const wasFirstSection = !id && state.sections.length === 0;
-  let newId = null;
-  if (id) await call("update_section", Number(id), ...args);
-  else newId = await call("create_section", ...args);
-  hide("sectionModal");
-  toast("Section saved");
-  // The first section ever created is the start of the setup flow, not the end
-  // of it: select it and go straight on to entering plots.
-  if (wasFirstSection && newId) state.sectionId = newId;
-  await refreshAll();
-  if (wasFirstSection && newId) await openGraveModal(null);
-});
-
-/* ---------- Grave modal ---------- */
-
-function sectionOptions(selectedId) {
-  // With "All sections" active selectedId is null, so fall back explicitly to
-  // the first section rather than letting the browser pick one silently.
-  const target = selectedId ?? (state.sections[0] && state.sections[0].id);
-  return state.sections.map((s) =>
-    `<option value="${s.id}" ${s.id === target ? "selected" : ""}>${esc(s.code)} · ${esc(s.name)}</option>`
-  ).join("");
-}
-
-async function openGraveModal(grave) {
-  // Always reload sections first so the dropdown can never offer a stale /
-  // deleted section id (which would fail the DB foreign-key constraint).
-  await refreshSections();
-  if (state.sections.length === 0) { promptForFirstSection(); return; }
-  el("graveModalTitle").textContent = grave ? "Edit Grave" : "Add Grave";
-  el("graveSection").innerHTML = sectionOptions(grave ? grave.section_id : state.sectionId);
-  el("graveId").value = grave ? grave.id : "";
-  el("gravePlot").value = grave ? grave.plot_number : "";
-  el("graveStatus").value = grave ? grave.status : "available";
-  el("graveOwner").value = grave ? grave.owner_name || "" : "";
-  el("graveContact").value = grave ? grave.owner_contact || "" : "";
-  el("graveNotes").value = grave ? grave.notes || "" : "";
-  el("graveRef").value = grave ? grave.grave_ref || "" : "";
-  el("graveDeed").value = grave ? grave.deed_id || "" : "";
-  el("gravePurchased").value = grave ? grave.date_purchased || "" : "";
-  show("graveModal");
-}
-
-el("graveForm").addEventListener("submit", async (e) => {
-  e.preventDefault();
-  const id = el("graveId").value;
-  const section = Number(el("graveSection").value);
-  if (!section) { toast("Please choose a section", true); return; }
-  // Order must match create_grave / update_grave in api.py.
-  const common = [
-    el("gravePlot").value,
-    el("graveStatus").value,
-    el("graveOwner").value,
-    el("graveContact").value,
-    el("graveNotes").value,
-    el("graveRef").value,
-    el("graveDeed").value,
-    el("gravePurchased").value,
-  ];
-  if (id) await call("update_grave", Number(id), section, ...common);
-  else await call("create_grave", section, ...common);
-  hide("graveModal");
-  toast("Grave saved");
-  await refreshAll();
-});
-
-/* ---------- Detail / burials modal ---------- */
-
-async function openDetail(graveId) {
-  const g = await call("get_grave", graveId);
-  el("detailTitle").textContent = `${g.section_code} · Plot ${g.plot_number}`;
-  el("detailMeta").innerHTML = `
-    <div><span>Status:</span> <span class="badge ${g.status}">${g.status}</span></div>
-    <div><span>Owner:</span> ${esc(g.owner_name || "—")} ${g.owner_contact ? "(" + esc(g.owner_contact) + ")" : ""}</div>
-    <div><span>Grave id:</span> ${esc(g.grave_ref || "—")}</div>
-    <div><span>Deed id:</span> ${esc(g.deed_id || "—")}</div>
-    <div><span>Purchased:</span> ${esc(g.date_purchased || "—")}</div>
-    <div><span>Notes:</span> ${esc(g.notes || "—")}</div>`;
-  el("burialGraveId").value = g.id;
-  renderBurials(g.burials);
-  el("burialForm").reset();
-  el("burialGraveId").value = g.id;
-  show("detailModal");
-}
-
-function renderBurials(burials) {
-  el("burialBody").innerHTML = burials.length
-    ? burials.map((b) => `
-      <tr>
-        <td>${esc(b.deceased_name)}</td>
-        <td>${esc(b.date_of_death || "—")}</td>
-        <td>${esc(b.date_of_burial || "—")}</td>
-        <td>${esc(b.notes || "")}</td>
-        <td class="actions-col">
-          <button class="btn link" data-docs-burial="${b.id}">docs${docBadge(b.doc_count)}</button>
-          <button class="btn link danger" data-del-burial="${b.id}">remove</button>
-        </td>
-      </tr>`).join("")
-    : `<tr><td colspan="5" class="empty">No burials recorded.</td></tr>`;
-}
-
-el("burialForm").addEventListener("submit", async (e) => {
-  e.preventDefault();
-  const graveId = Number(el("burialGraveId").value);
-  await call("add_burial", graveId, el("burialName").value,
-    el("burialDeath").value, el("burialBurial").value, el("burialNotes").value);
-  toast("Burial recorded — grave marked occupied");
-  await openDetail(graveId);
-  await refreshAll();
-});
-
-/* ---------- Documents modal ---------- */
-
-/* One modal serves sections, graves and burials; only the owner changes. */
-async function openDocuments(ownerType, ownerId, title) {
-  state.docOwner = { type: ownerType, id: ownerId, title };
-  el("documentsTitle").textContent = `Documents — ${title}`;
-  await refreshDocuments();
-  show("documentsModal");
-}
-
-async function refreshDocuments() {
-  const { type, id } = state.docOwner;
-  renderDocuments(await call("list_documents", type, id));
-}
-
-function renderDocuments(docs) {
-  el("documentBody").innerHTML = docs.length
-    ? docs.map((d) => `
-      <tr>
-        <td><button class="doc-name" data-doc-open="${d.id}"
-                    title="Open in the default application">${esc(d.original_name)}</button></td>
-        <td>${fileSize(d.size_bytes)}</td>
-        <td>${esc((d.created_at || "").slice(0, 10))}</td>
-        <td class="actions-col">
-          <button class="btn link danger" data-doc-del="${d.id}">remove</button>
-        </td>
-      </tr>`).join("")
-    : `<tr><td colspan="4" class="empty">No documents attached yet.</td></tr>`;
-}
-
-el("uploadDocBtn").addEventListener("click", async () => {
-  const { type, id } = state.docOwner;
-  // The native picker runs in Python; no file bytes cross this bridge.
-  const added = await call("add_documents", type, id);
-  if (added.length) {
-    toast(`${added.length} document${added.length === 1 ? "" : "s"} attached`);
-    await refreshDocuments();
-    await refreshAll();
-  }
-});
-
-/* ---------- Global event delegation ---------- */
-
-document.addEventListener("click", async (e) => {
-  const t = e.target;
-
-  // Close only the modal that was clicked: the documents modal can sit on top
-  // of the grave detail modal, which should survive it.
-  if (t.dataset.close !== undefined) { closeModalAround(t); return; }
-  if (t.classList.contains("modal-backdrop")) { t.hidden = true; return; }
-
-  // Empty-state calls to action
-  if (t.dataset.onboardSection !== undefined) { openSectionModal(null); return; }
-  if (t.dataset.onboardGrave !== undefined) { await openGraveModal(null); return; }
-  if (t.dataset.clearFilters !== undefined) {
-    state.sectionId = null;
-    state.status = "";
-    state.search = "";
-    el("statusFilter").value = "";
-    el("searchInput").value = "";
-    await refreshSections();
-    await refreshGraves();
-    return;
-  }
-
-  // Documents
-  if (t.dataset.docsSection) {
-    const s = state.sections.find((x) => x.id === Number(t.dataset.docsSection));
-    await openDocuments("section", Number(t.dataset.docsSection),
-      s ? `${s.code} · ${s.name}` : "Section");
-    return;
-  }
-  if (t.dataset.docsGrave) {
-    const g = await call("get_grave", Number(t.dataset.docsGrave));
-    await openDocuments("grave", g.id, `${g.section_code} · Plot ${g.plot_number}`);
-    return;
-  }
-  if (t.dataset.docsBurial) {
-    await openDocuments("burial", Number(t.dataset.docsBurial), "Burial record");
-    return;
-  }
-  if (t.dataset.docOpen) {
-    await call("open_document", Number(t.dataset.docOpen));
-    return;
-  }
-  if (t.dataset.docDel) {
-    if (confirm("Remove this document? The file is deleted from the store.")) {
-      await call("delete_document", Number(t.dataset.docDel));
-      toast("Document removed");
-      await refreshDocuments();
-      await refreshAll();
-    }
-    return;
-  }
-
-  // Section row / edit
-  if (t.dataset.editSection) {
-    const s = state.sections.find((x) => x.id === Number(t.dataset.editSection));
-    openSectionModal(s);
-    return;
-  }
-  const li = t.closest("li[data-id]");
-  if (li) {
-    state.sectionId = li.dataset.id ? Number(li.dataset.id) : null;
-    await refreshSections();
-    await refreshGraves();
-    return;
-  }
-
-  // Grave actions
-  if (t.dataset.detail) return void openDetail(Number(t.dataset.detail));
-  if (t.dataset.edit) {
-    const g = await call("get_grave", Number(t.dataset.edit));
-    openGraveModal(g);
-    return;
-  }
-  if (t.dataset.del) {
-    if (await confirmDelete("grave", Number(t.dataset.del), "this plot")) {
-      await call("delete_grave", Number(t.dataset.del));
-      toast("Grave deleted");
-      await refreshAll();
-    }
-    return;
-  }
-  if (t.dataset.delBurial) {
-    if (await confirmDelete("burial", Number(t.dataset.delBurial), "this burial record")) {
-      await call("delete_burial", Number(t.dataset.delBurial));
-      await openDetail(Number(el("burialGraveId").value));
-      await refreshAll();
-    }
-    return;
-  }
-});
-
-el("addSectionBtn").addEventListener("click", () => openSectionModal(null));
-el("addGraveBtn").addEventListener("click", () => {
-  if (state.sections.length === 0) return promptForFirstSection();
-  openGraveModal(null);
-});
-
-/* A plot cannot exist without a section, so say why and open the form that
- * fixes it rather than leaving the user with a toast and no next step. */
-function promptForFirstSection() {
-  toast("Create a section first — every plot belongs to one", true);
-  openSectionModal(null);
-}
-el("searchInput").addEventListener("input", debounce((e) => {
-  state.search = e.target.value;
-  refreshGraves();
-}, 200));
-el("statusFilter").addEventListener("change", (e) => {
-  state.status = e.target.value;
-  refreshGraves();
-});
-
-/* ---------- Helpers ---------- */
-
-/* Names what a delete takes with it, so attached paperwork is never a surprise. */
-async function confirmDelete(ownerType, id, what) {
-  const c = await call("describe_delete", ownerType, id);
-  const parts = [];
-  if (c.graves) parts.push(plural(c.graves, "plot"));
-  if (c.burials) parts.push(plural(c.burials, "burial record"));
-  if (c.documents) parts.push(plural(c.documents, "document"));
-  const tail = parts.length ? `, along with ${parts.join(", ")}` : "";
-  return confirm(`Delete ${what}${tail}? This cannot be undone.`);
-}
-
-function plural(n, word) { return `${n} ${word}${n === 1 ? "" : "s"}`; }
-function docBadge(n) { return n ? ` (${n})` : ""; }
-function fileSize(bytes) {
-  if (bytes < 1024) return `${bytes} B`;
-  if (bytes < 1048576) return `${Math.round(bytes / 1024)} KB`;
-  return `${(bytes / 1048576).toFixed(1)} MB`;
-}
-
-function show(id) { el(id).hidden = false; }
-function hide(id) { el(id).hidden = true; }
-function closeModalAround(node) {
-  const modal = node.closest(".modal-backdrop");
-  if (modal) modal.hidden = true;
-}
-function esc(s) {
-  return String(s).replace(/[&<>"']/g, (c) =>
-    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
-}
-function debounce(fn, ms) {
-  let h;
-  return (...a) => { clearTimeout(h); h = setTimeout(() => fn(...a), ms); };
-}
-let toastTimer;
-function toast(msg, isError = false) {
-  const t = el("toast");
-  t.textContent = msg;
-  t.className = "toast" + (isError ? " error" : "");
-  t.hidden = false;
-  clearTimeout(toastTimer);
-  toastTimer = setTimeout(() => (t.hidden = true), 3000);
-}
-
-/* pywebview injects its API asynchronously. Load as soon as it is available —
- * handle the case where `pywebviewready` already fired before this script ran. */
-function start() { refreshAll().catch((e) => console.error(e)); }
-if (window.pywebview && window.pywebview.api) start();
-else window.addEventListener("pywebviewready", start);
+"use strict";
+
+/* ---------- Global event delegation ---------- */
+
+/* The owner modal can be dismissed (Cancel or backdrop click) instead of
+ * saved. Without this, a flag set by "+ New owner..." on the grave form
+ * would survive the cancel and get consumed by some later, unrelated owner
+ * save elsewhere in the app. Not cleared inside openOwnerModal itself: the
+ * grave-form path sets the flag and *then* calls openOwnerModal(null), so
+ * clearing on open would wipe the flag it just set. */
+function clearOwnerReturnOnDismiss(modal) {
+  if (modal && modal.id === "ownerModal") state.ownerReturnsToGrave = false;
+}
+
+document.addEventListener("click", async (e) => {
+  const t = e.target;
+
+  // Close only the modal that was clicked: the documents modal can sit on top
+  // of the grave detail modal, which should survive it.
+  if (t.dataset.close !== undefined) {
+    clearOwnerReturnOnDismiss(t.closest(".modal-backdrop"));
+    closeModalAround(t);
+    return;
+  }
+  if (t.classList.contains("modal-backdrop")) {
+    clearOwnerReturnOnDismiss(t);
+    t.hidden = true;
+    return;
+  }
+
+  // Empty-state calls to action
+  if (t.dataset.onboardSection !== undefined) { openSectionModal(null); return; }
+  if (t.dataset.onboardGrave !== undefined) { await openGraveModal(null); return; }
+  if (t.dataset.clearFilters !== undefined) {
+    state.sectionId = null;
+    state.status = "";
+    state.search = "";
+    el("statusFilter").value = "";
+    el("searchInput").value = "";
+    await refreshSections();
+    await refreshGraves();
+    return;
+  }
+
+  // Documents
+  if (t.dataset.docsSection) {
+    const s = state.sections.find((x) => x.id === Number(t.dataset.docsSection));
+    await openDocuments("section", Number(t.dataset.docsSection),
+      s ? `${s.code} · ${s.name}` : "Section");
+    return;
+  }
+  if (t.dataset.docsGrave) {
+    const g = await call("get_grave", Number(t.dataset.docsGrave));
+    await openDocuments("grave", g.id, `${g.section_code} · Plot ${g.plot_number}`);
+    return;
+  }
+  if (t.dataset.docsBurial) {
+    await openDocuments("burial", Number(t.dataset.docsBurial), "Burial record");
+    return;
+  }
+  if (t.dataset.docOpen) {
+    await call("open_document", Number(t.dataset.docOpen));
+    return;
+  }
+  if (t.dataset.docDel) {
+    if (confirm("Remove this document? The file is deleted from the store.")) {
+      await call("delete_document", Number(t.dataset.docDel));
+      toast("Document removed");
+      await refreshDocuments();
+      await refreshAll();
+    }
+    return;
+  }
+
+  // Section row / edit
+  if (t.dataset.editSection) {
+    const s = state.sections.find((x) => x.id === Number(t.dataset.editSection));
+    openSectionModal(s);
+    return;
+  }
+  if (t.dataset.tab) { setTab(t.dataset.tab); return; }
+  if (t.dataset.addOwner !== undefined) { openOwnerModal(null); return; }
+  if (t.dataset.editOwner) {
+    const o = await call("get_owner", Number(t.dataset.editOwner));
+    openOwnerModal(o);
+    return;
+  }
+  const ownerLi = t.closest("li[data-owner-id]");
+  if (ownerLi) {
+    state.ownerId = ownerLi.dataset.ownerId ? Number(ownerLi.dataset.ownerId) : null;
+    state.sectionId = null;   // the two filters are mutually exclusive
+    await refreshOwners();
+    await refreshSections();
+    await refreshGraves();
+    return;
+  }
+
+  const li = t.closest("li[data-id]");
+  if (li) {
+    state.sectionId = li.dataset.id ? Number(li.dataset.id) : null;
+    state.ownerId = null;
+    await refreshSections();
+    await refreshOwners();
+    await refreshGraves();
+    return;
+  }
+
+  // Grave actions
+  if (t.dataset.detail) return void openDetail(Number(t.dataset.detail));
+  if (t.dataset.edit) {
+    const g = await call("get_grave", Number(t.dataset.edit));
+    openGraveModal(g);
+    return;
+  }
+  if (t.dataset.del) {
+    if (await confirmDelete("grave", Number(t.dataset.del), "this plot")) {
+      await call("delete_grave", Number(t.dataset.del));
+      toast("Grave deleted");
+      await refreshAll();
+    }
+    return;
+  }
+  if (t.dataset.delBurial) {
+    if (await confirmDelete("burial", Number(t.dataset.delBurial), "this burial record")) {
+      await call("delete_burial", Number(t.dataset.delBurial));
+      await openDetail(Number(el("burialGraveId").value));
+      await refreshAll();
+    }
+    return;
+  }
+});
+
+el("addSectionBtn").addEventListener("click", () => openSectionModal(null));
+el("addOwnerBtn").addEventListener("click", () => openOwnerModal(null));
+el("addGraveBtn").addEventListener("click", () => {
+  if (state.sections.length === 0) return promptForFirstSection();
+  openGraveModal(null);
+});
+
+el("searchInput").addEventListener("input", debounce((e) => {
+  state.search = e.target.value;
+  refreshGraves();
+}, 200));
+el("statusFilter").addEventListener("change", (e) => {
+  state.status = e.target.value;
+  refreshGraves();
+});
+
+/* pywebview injects its API asynchronously. Load as soon as it is available —
+ * handle the case where `pywebviewready` already fired before this script ran. */
+function start() { refreshAll().catch((e) => console.error(e)); }
+if (window.pywebview && window.pywebview.api) start();
+else window.addEventListener("pywebviewready", start);
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/documents.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/documents.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/documents.js	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/documents.js	2026-09-21 08:22:05.634806400 -0400
@@ -0,0 +1,42 @@
+"use strict";
+
+/* ---------- Documents modal ---------- */
+
+/* One modal serves sections, graves and burials; only the owner changes. */
+async function openDocuments(ownerType, ownerId, title) {
+  state.docOwner = { type: ownerType, id: ownerId, title };
+  el("documentsTitle").textContent = `Documents — ${title}`;
+  await refreshDocuments();
+  show("documentsModal");
+}
+
+async function refreshDocuments() {
+  const { type, id } = state.docOwner;
+  renderDocuments(await call("list_documents", type, id));
+}
+
+function renderDocuments(docs) {
+  el("documentBody").innerHTML = docs.length
+    ? docs.map((d) => `
+      <tr>
+        <td><button class="doc-name" data-doc-open="${d.id}"
+                    title="Open in the default application">${esc(d.original_name)}</button></td>
+        <td>${fileSize(d.size_bytes)}</td>
+        <td>${esc((d.created_at || "").slice(0, 10))}</td>
+        <td class="actions-col">
+          <button class="btn link danger" data-doc-del="${d.id}">remove</button>
+        </td>
+      </tr>`).join("")
+    : `<tr><td colspan="4" class="empty">No documents attached yet.</td></tr>`;
+}
+
+el("uploadDocBtn").addEventListener("click", async () => {
+  const { type, id } = state.docOwner;
+  // The native picker runs in Python; no file bytes cross this bridge.
+  const added = await call("add_documents", type, id);
+  if (added.length) {
+    toast(`${added.length} document${added.length === 1 ? "" : "s"} attached`);
+    await refreshDocuments();
+    await refreshAll();
+  }
+});
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/graves.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/graves.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/graves.js	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/graves.js	2026-09-21 09:02:08.788113600 -0400
@@ -0,0 +1,137 @@
+"use strict";
+
+async function refreshGraves() {
+  const graves = await call("list_graves", state.sectionId, state.status,
+                            state.search, state.ownerId);
+  const body = el("graveBody");
+  body.innerHTML = graves.map((g) => `
+    <tr>
+      <td>${esc(g.section_code)}</td>
+      <td>${esc(g.plot_number)}</td>
+      <td><span class="badge ${g.status}">${g.status}</span></td>
+      <td>${esc(g.owner_name || "—")}</td>
+      <td class="actions-col">
+        <button class="btn link" data-docs-grave="${g.id}">Docs${docBadge(g.doc_count)}</button>
+        <button class="btn link" data-detail="${g.id}">Burials</button>
+        <button class="btn link" data-edit="${g.id}">Edit</button>
+        <button class="btn link danger" data-del="${g.id}">Delete</button>
+      </td>
+    </tr>`).join("");
+  renderEmptyState(graves.length);
+}
+
+/* ---------- Grave modal ---------- */
+
+function sectionOptions(selectedId) {
+  // With "All sections" active selectedId is null, so fall back explicitly to
+  // the first section rather than letting the browser pick one silently.
+  const target = selectedId ?? (state.sections[0] && state.sections[0].id);
+  return state.sections.map((s) =>
+    `<option value="${s.id}" ${s.id === target ? "selected" : ""}>${esc(s.code)} · ${esc(s.name)}</option>`
+  ).join("");
+}
+
+async function openGraveModal(grave) {
+  // Always reload sections first so the dropdown can never offer a stale /
+  // deleted section id (which would fail the DB foreign-key constraint).
+  await refreshSections();
+  if (state.sections.length === 0) { promptForFirstSection(); return; }
+  el("graveModalTitle").textContent = grave ? "Edit Grave" : "Add Grave";
+  el("graveSection").innerHTML = sectionOptions(grave ? grave.section_id : state.sectionId);
+  el("graveId").value = grave ? grave.id : "";
+  el("gravePlot").value = grave ? grave.plot_number : "";
+  el("graveStatus").value = grave ? grave.status : "available";
+  el("graveNotes").value = grave ? grave.notes || "" : "";
+  el("graveRef").value = grave ? grave.grave_ref || "" : "";
+  el("graveDeed").value = grave ? grave.deed_id || "" : "";
+  el("gravePurchased").value = grave ? grave.date_purchased || "" : "";
+  await refreshOwners();             // never offer a stale or deleted owner
+  fillOwnerOptions(grave ? grave.owner_id : null);
+  show("graveModal");
+}
+
+/* The trailing "+ New owner…" entry opens the owner modal and returns here
+ * with the new owner selected, so grave entry is never interrupted. */
+function fillOwnerOptions(selectedId) {
+  el("graveOwnerSelect").innerHTML =
+    `<option value="">— no owner —</option>` +
+    state.owners.map((o) =>
+      `<option value="${o.id}" ${o.id === selectedId ? "selected" : ""}>${esc(o.name)}</option>`
+    ).join("") +
+    `<option value="__new">+ New owner…</option>`;
+  el("graveOwnerSelect").value = selectedId ? String(selectedId) : "";
+}
+
+el("graveOwnerSelect").addEventListener("change", (e) => {
+  if (e.target.value !== "__new") return;
+  e.target.value = "";               // never leave the sentinel selected
+  state.ownerReturnsToGrave = true;
+  openOwnerModal(null);
+});
+
+el("graveForm").addEventListener("submit", async (e) => {
+  e.preventDefault();
+  const id = el("graveId").value;
+  const section = Number(el("graveSection").value);
+  if (!section) { toast("Please choose a section", true); return; }
+  // Order must match create_grave / update_grave in api.py.
+  const common = [
+    el("gravePlot").value,
+    el("graveStatus").value,
+    el("graveOwnerSelect").value,     // "" means unassigned -> NULL
+    el("graveNotes").value,
+    el("graveRef").value,
+    el("graveDeed").value,
+    el("gravePurchased").value,
+  ];
+  if (id) await call("update_grave", Number(id), section, ...common);
+  else await call("create_grave", section, ...common);
+  hide("graveModal");
+  toast("Grave saved");
+  await refreshAll();
+});
+
+/* ---------- Detail / burials modal ---------- */
+
+async function openDetail(graveId) {
+  const g = await call("get_grave", graveId);
+  el("detailTitle").textContent = `${g.section_code} · Plot ${g.plot_number}`;
+  el("detailMeta").innerHTML = `
+    <div><span>Status:</span> <span class="badge ${g.status}">${g.status}</span></div>
+    <div><span>Owner:</span> ${esc(g.owner_name || "—")} ${g.owner_contact ? "(" + esc(g.owner_contact) + ")" : ""}</div>
+    <div><span>Grave id:</span> ${esc(g.grave_ref || "—")}</div>
+    <div><span>Deed id:</span> ${esc(g.deed_id || "—")}</div>
+    <div><span>Purchased:</span> ${esc(g.date_purchased || "—")}</div>
+    <div><span>Notes:</span> ${esc(g.notes || "—")}</div>`;
+  el("burialGraveId").value = g.id;
+  renderBurials(g.burials);
+  el("burialForm").reset();
+  el("burialGraveId").value = g.id;
+  show("detailModal");
+}
+
+function renderBurials(burials) {
+  el("burialBody").innerHTML = burials.length
+    ? burials.map((b) => `
+      <tr>
+        <td>${esc(b.deceased_name)}</td>
+        <td>${esc(b.date_of_death || "—")}</td>
+        <td>${esc(b.date_of_burial || "—")}</td>
+        <td>${esc(b.notes || "")}</td>
+        <td class="actions-col">
+          <button class="btn link" data-docs-burial="${b.id}">docs${docBadge(b.doc_count)}</button>
+          <button class="btn link danger" data-del-burial="${b.id}">remove</button>
+        </td>
+      </tr>`).join("")
+    : `<tr><td colspan="5" class="empty">No burials recorded.</td></tr>`;
+}
+
+el("burialForm").addEventListener("submit", async (e) => {
+  e.preventDefault();
+  const graveId = Number(el("burialGraveId").value);
+  await call("add_burial", graveId, el("burialName").value,
+    el("burialDeath").value, el("burialBurial").value, el("burialNotes").value);
+  toast("Burial recorded — grave marked occupied");
+  await openDetail(graveId);
+  await refreshAll();
+});
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/owners.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/owners.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/owners.js	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/owners.js	2026-09-21 08:55:51.805618300 -0400
@@ -0,0 +1,81 @@
+"use strict";
+
+async function refreshOwners() {
+  const owners = await call("list_owners");
+  state.owners = owners;
+  // No owners yet: say so and offer the action, matching the grave empty state.
+  if (owners.length === 0) {
+    el("ownerList").innerHTML = `
+      <li class="owner-empty">
+        <div class="sec-name">No owners recorded yet</div>
+        <div class="sec-meta"><span>Plots can be filed under an owner.</span></div>
+        <button class="btn small primary" data-add-owner>Add owner</button>
+      </li>`;
+    return;
+  }
+  el("ownerList").innerHTML = `<li class="${state.ownerId === null ? "active" : ""}" data-owner-id="">
+      <div class="sec-name">All owners</div>
+      <div class="sec-meta"><span>Show every plot</span></div></li>` +
+    owners.map((o) => `
+    <li class="${state.ownerId === o.id ? "active" : ""}" data-owner-id="${o.id}">
+      <button class="btn link sec-edit" data-edit-owner="${o.id}">edit</button>
+      <div class="sec-name">${esc(o.name)}</div>
+      <div class="sec-meta">
+        <span>${plural(o.grave_count, "plot")}</span>
+        <span>${esc(o.contact || "")}</span>
+      </div>
+    </li>`).join("");
+}
+
+function openOwnerModal(owner) {
+  el("ownerModalTitle").textContent = owner ? "Edit Owner" : "Add Owner";
+  el("ownerId").value = owner ? owner.id : "";
+  el("ownerName").value = owner ? owner.name : "";
+  el("ownerContact").value = owner ? owner.contact || "" : "";
+  el("ownerAddress").value = owner ? owner.address || "" : "";
+  el("ownerNotes").value = owner ? owner.notes || "" : "";
+  el("deleteOwnerBtn").hidden = !owner;
+  show("ownerModal");
+}
+
+el("ownerForm").addEventListener("submit", async (e) => {
+  e.preventDefault();
+  const id = el("ownerId").value;
+  const args = [el("ownerName").value, el("ownerContact").value,
+                el("ownerAddress").value, el("ownerNotes").value];
+  let newId = null;
+  if (id) await call("update_owner", Number(id), ...args);
+  else newId = await call("create_owner", ...args);
+  hide("ownerModal");
+  toast("Owner saved");
+  await refreshOwners();
+  // Opened from the grave form: hand the new owner straight back to it.
+  // `fillOwnerOptions` arrives in Task 6, so this is guarded — between Task 5
+  // and Task 6 the inline path simply does nothing rather than throwing.
+  if (newId && state.ownerReturnsToGrave) {
+    state.ownerReturnsToGrave = false;
+    if (typeof fillOwnerOptions === "function") fillOwnerOptions(newId);
+  }
+  await refreshAll();
+});
+
+el("deleteOwnerBtn").addEventListener("click", async () => {
+  const id = Number(el("ownerId").value);
+  if (!confirm("Delete this owner?")) return;
+  await call("delete_owner", id);   // refused by the API if they hold plots
+  hide("ownerModal");
+  toast("Owner deleted");
+  if (state.ownerId === id) state.ownerId = null;
+  await refreshOwners();
+  await refreshAll();
+});
+
+function setTab(name) {
+  state.tab = name;
+  document.querySelectorAll(".tab").forEach(
+    (t) => t.classList.toggle("active", t.dataset.tab === name));
+  el("sectionList").hidden = name !== "sections";
+  el("ownerList").hidden = name !== "owners";
+  el("addSectionBtn").hidden = name !== "sections";
+  el("addOwnerBtn").hidden = name !== "owners";
+}
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/sections.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/sections.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/sections.js	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/sections.js	2026-09-21 08:21:48.859446100 -0400
@@ -0,0 +1,54 @@
+"use strict";
+
+async function refreshSections() {
+  state.sections = await call("list_sections");
+  const list = el("sectionList");
+  const all = `<li class="${state.sectionId === null ? "active" : ""}" data-id="">
+      <div class="sec-name">All sections</div>
+      <div class="sec-meta"><span>Show every plot</span></div></li>`;
+  list.innerHTML = all + state.sections.map((s) => `
+    <li class="${state.sectionId === s.id ? "active" : ""}" data-id="${s.id}">
+      <button class="btn link sec-edit" data-edit-section="${s.id}">edit</button>
+      <button class="btn link sec-edit" data-docs-section="${s.id}">docs${docBadge(s.doc_count)}</button>
+      <div class="sec-name">${esc(s.code)} · ${esc(s.name)}</div>
+      <div class="sec-meta">
+        <span>${s.total_plots} plots</span>
+        <span>${s.available_plots || 0} free</span>
+      </div>
+    </li>`).join("");
+}
+
+/* ---------- Section modal ---------- */
+
+function openSectionModal(section) {
+  el("sectionModalTitle").textContent = section ? "Edit Section" : "Add Section";
+  el("sectionId").value = section ? section.id : "";
+  el("sectionCode").value = section ? section.code : "";
+  el("sectionName").value = section ? section.name : "";
+  el("sectionDesc").value = section ? section.description || "" : "";
+  show("sectionModal");
+}
+
+el("sectionForm").addEventListener("submit", async (e) => {
+  e.preventDefault();
+  const id = el("sectionId").value;
+  const args = [el("sectionCode").value, el("sectionName").value, el("sectionDesc").value];
+  const wasFirstSection = !id && state.sections.length === 0;
+  let newId = null;
+  if (id) await call("update_section", Number(id), ...args);
+  else newId = await call("create_section", ...args);
+  hide("sectionModal");
+  toast("Section saved");
+  // The first section ever created is the start of the setup flow, not the end
+  // of it: select it and go straight on to entering plots.
+  if (wasFirstSection && newId) state.sectionId = newId;
+  await refreshAll();
+  if (wasFirstSection && newId) await openGraveModal(null);
+});
+
+/* A plot cannot exist without a section, so say why and open the form that
+ * fixes it rather than leaving the user with a toast and no next step. */
+function promptForFirstSection() {
+  toast("Create a section first — every plot belongs to one", true);
+  openSectionModal(null);
+}
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/state.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/state.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/state.js	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/state.js	2026-09-21 08:55:56.961935800 -0400
@@ -0,0 +1,70 @@
+"use strict";
+
+let state = { sectionId: null, status: "", search: "", sections: [], totalGraves: 0,
+              docOwner: { type: null, id: null, title: "" },
+              tab: "sections", ownerId: null, owners: [], ownerReturnsToGrave: false };
+
+/* ---------- Rendering ---------- */
+
+async function refreshStats() {
+  const s = await call("stats");
+  // Remembered so the empty state can tell "nothing recorded yet" apart from
+  // "records exist but the filters hide them".
+  state.totalGraves = s.total;
+  el("stats").innerHTML = `
+    <div><b>${s.total}</b>Total plots</div>
+    <div><b>${s.available}</b>Available</div>
+    <div><b>${s.reserved}</b>Reserved</div>
+    <div><b>${s.occupied}</b>Occupied</div>
+    <div><b>${s.sections}</b>Sections</div>`;
+}
+
+/* An empty table means one of three different things. Saying which one, and
+ * offering the action that resolves it, is the difference between a dead end
+ * and a next step. */
+function renderEmptyState(graveCount) {
+  const firstRun = state.sections.length === 0;
+  const box = el("emptyState");
+
+  // On first run there is nothing to search, filter or list yet.
+  el("toolbar").hidden = firstRun;
+  el("graveTable").hidden = firstRun || graveCount === 0;
+
+  if (firstRun) {
+    box.innerHTML = `
+      <h2>Welcome to Grave Inventory</h2>
+      <p>Plots belong to a section, so start by creating one &mdash; for example
+         <b>A &middot; Garden of Peace</b>. You can add plots to it straight after.</p>
+      <button class="btn primary" data-onboard-section>Create first section</button>`;
+  } else if (graveCount > 0) {
+    box.hidden = true;
+    return;
+  } else if (state.totalGraves > 0) {
+    box.innerHTML = `
+      <p>No graves match the current filters.</p>
+      <button class="btn" data-clear-filters>Clear filters</button>`;
+  } else {
+    box.innerHTML = `
+      <p>No plots recorded yet.</p>
+      <button class="btn primary" data-onboard-grave>Add the first grave</button>`;
+  }
+  box.hidden = false;
+}
+
+async function refreshAll() {
+  // Sections must land before graves: the empty state can only choose its
+  // message once it knows whether any section exists.
+  await Promise.all([refreshStats(), refreshSections(), refreshOwners()]);
+  await refreshGraves();
+}
+
+/* Names what a delete takes with it, so attached paperwork is never a surprise. */
+async function confirmDelete(ownerType, id, what) {
+  const c = await call("describe_delete", ownerType, id);
+  const parts = [];
+  if (c.graves) parts.push(plural(c.graves, "plot"));
+  if (c.burials) parts.push(plural(c.burials, "burial record"));
+  if (c.documents) parts.push(plural(c.documents, "document"));
+  const tail = parts.length ? `, along with ${parts.join(", ")}` : "";
+  return confirm(`Delete ${what}${tail}? This cannot be undone.`);
+}
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/util.js C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/util.js
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/graveyard/web/js/util.js	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/graveyard/web/js/util.js	2026-09-21 08:21:35.017199400 -0400
@@ -0,0 +1,36 @@
+"use strict";
+
+const $ = (sel) => document.querySelector(sel);
+const el = (id) => document.getElementById(id);
+
+function plural(n, word) { return `${n} ${word}${n === 1 ? "" : "s"}`; }
+function docBadge(n) { return n ? ` (${n})` : ""; }
+function fileSize(bytes) {
+  if (bytes < 1024) return `${bytes} B`;
+  if (bytes < 1048576) return `${Math.round(bytes / 1024)} KB`;
+  return `${(bytes / 1048576).toFixed(1)} MB`;
+}
+
+function show(id) { el(id).hidden = false; }
+function hide(id) { el(id).hidden = true; }
+function closeModalAround(node) {
+  const modal = node.closest(".modal-backdrop");
+  if (modal) modal.hidden = true;
+}
+function esc(s) {
+  return String(s).replace(/[&<>"']/g, (c) =>
+    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
+}
+function debounce(fn, ms) {
+  let h;
+  return (...a) => { clearTimeout(h); h = setTimeout(() => fn(...a), ms); };
+}
+let toastTimer;
+function toast(msg, isError = false) {
+  const t = el("toast");
+  t.textContent = msg;
+  t.className = "toast" + (isError ? " error" : "");
+  t.hidden = false;
+  clearTimeout(toastTimer);
+  toastTimer = setTimeout(() => (t.hidden = true), 3000);
+}
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/tests/test_graves.py C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/tests/test_graves.py
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/tests/test_graves.py	2026-09-20 18:42:09.049965500 -0400
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/tests/test_graves.py	2026-09-21 08:49:47.813275600 -0400
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
diff -ruN '--exclude=__pycache__' C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/tests/test_owners.py C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/tests/test_owners.py
--- C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\task-1-base/tests/test_owners.py	1969-12-31 19:00:00.000000000 -0500
+++ C:\ClaudeCode\funeral\.superpowers\sdd\2026-09-21-grave-owners\snapshots\final-head/tests/test_owners.py	2026-09-21 08:49:28.015961700 -0400
@@ -0,0 +1,317 @@
+"""Tests for the owners table and the owner-migration.
+
+Run: python tests/test_owners.py
+"""
+
+import gc
+import os
+import shutil
+import sqlite3
+import sys
+import tempfile
+from pathlib import Path
+
+ROOT = Path(__file__).resolve().parent.parent
+sys.path.insert(0, str(ROOT))
+
+TMP = Path(tempfile.mkdtemp(prefix="graveyard-owners-"))
+DB = TMP / "test.db"
+os.environ["GRAVEYARD_DB"] = str(DB)
+
+from graveyard.api import Api  # noqa: E402
+from graveyard.database import get_connection, init_db  # noqa: E402
+
+PASS, FAIL = [], []
+
+OLD_GRAVES = """
+CREATE TABLE sections (
+    id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL UNIQUE,
+    name TEXT NOT NULL, description TEXT,
+    created_at TEXT NOT NULL DEFAULT (datetime('now')));
+CREATE TABLE graves (
+    id INTEGER PRIMARY KEY AUTOINCREMENT,
+    section_id INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
+    plot_number TEXT NOT NULL,
+    status TEXT NOT NULL DEFAULT 'available'
+           CHECK (status IN ('available','reserved','occupied')),
+    owner_name TEXT, owner_contact TEXT, notes TEXT,
+    grave_ref TEXT NOT NULL DEFAULT '', deed_id TEXT NOT NULL DEFAULT '',
+    date_purchased TEXT NOT NULL DEFAULT '',
+    created_at TEXT NOT NULL DEFAULT (datetime('now')),
+    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
+    UNIQUE (section_id, plot_number));
+"""
+
+
+def check(name, fn):
+    try:
+        fn()
+    except Exception as exc:
+        FAIL.append(f"{name}: {type(exc).__name__}: {exc}")
+    else:
+        PASS.append(name)
+
+
+def ok(res):
+    assert res["ok"], f"expected ok, got error: {res.get('error')}"
+    return res["data"]
+
+
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
+def _build_old_db():
+    """A pre-owners database exercising every "no owner" and dedupe path:
+    a duplicate name with two contacts, a whitespace-padded duplicate of
+    that same name, a blank name, a whitespace-only name, and a NULL name
+    (the column is nullable in the old schema)."""
+    if DB.exists():
+        DB.unlink()
+    conn = sqlite3.connect(DB)
+    conn.executescript(OLD_GRAVES)
+    conn.execute("INSERT INTO sections (code, name) VALUES ('A','Garden')")
+    for plot, name, contact in [
+        ("1", "Aftab Dar", "222-444-777"),        # lowest id wins
+        ("2", "Aftab Dar", "222-555-7777"),       # discarded
+        ("3", "Margaret Whitfield", "555-0142"),
+        ("4", "", ""),                             # blank: stays unassigned
+        ("5", " Aftab Dar ", "999-999-9999"),     # padded dupe: must merge via TRIM
+        ("6", "   ", "111-111-1111"),             # whitespace-only: stays unassigned
+    ]:
+        conn.execute(
+            "INSERT INTO graves (section_id, plot_number, owner_name, owner_contact)"
+            " VALUES (1, ?, ?, ?)", (plot, name, contact))
+    conn.execute(
+        "INSERT INTO graves (section_id, plot_number, owner_name, owner_contact)"
+        " VALUES (1, '7', NULL, NULL)")            # NULL name: stays unassigned
+    conn.commit()
+    conn.close()
+
+
+def t_migration_creates_owners_and_dedupes():
+    _build_old_db()
+    init_db()
+    with get_connection() as c:
+        owners = [dict(r) for r in c.execute("SELECT * FROM owners ORDER BY name")]
+        graves = [dict(r) for r in c.execute(
+            "SELECT plot_number, owner_id FROM graves ORDER BY plot_number")]
+        cols = {r["name"] for r in c.execute("PRAGMA table_info(graves)")}
+
+    assert [o["name"] for o in owners] == ["Aftab Dar", "Margaret Whitfield"], owners
+    aftab = owners[0]
+    assert aftab["contact"] == "222-444-777", f"first contact must win: {aftab}"
+
+    by_plot = {g["plot_number"]: g["owner_id"] for g in graves}
+    assert by_plot["1"] == aftab["id"] and by_plot["2"] == aftab["id"], by_plot
+    assert by_plot["5"] == aftab["id"], "whitespace-padded duplicate must merge via TRIM"
+    assert by_plot["4"] is None, "blank owner must stay unassigned"
+    assert by_plot["6"] is None, "whitespace-only owner must stay unassigned"
+    assert by_plot["7"] is None, "NULL owner must stay unassigned"
+    assert "owner_name" not in cols and "owner_contact" not in cols, cols
+
+
+def t_migration_is_idempotent():
+    _build_old_db()
+    init_db()
+    with get_connection() as c:
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
+
+
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
+if __name__ == "__main__":
+    for name, fn in sorted(globals().items()):
+        if name.startswith("t_"):
+            check(name[2:], fn)
+    for n in PASS:
+        print(f"  [PASS] {n}")
+    for f in FAIL:
+        print(f"  [FAIL] {f}")
+    print(f"RESULT {len(PASS)}/{len(PASS) + len(FAIL)} passed")
+    shutil.rmtree(TMP, ignore_errors=True)
+    sys.exit(1 if FAIL else 0)

```