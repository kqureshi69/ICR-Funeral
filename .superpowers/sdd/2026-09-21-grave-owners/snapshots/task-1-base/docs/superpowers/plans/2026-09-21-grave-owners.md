# Grave Owners Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace free-text grave ownership with first-class owner records, so a grave is filed under an owner and one owner can hold many graves.

**Architecture:** A new `owners` table; `graves` gains a nullable `owner_id` foreign key and loses `owner_name` / `owner_contact`. A one-time migration folds existing owner text into owner records, deduplicating by trimmed name. The sidebar gains a Sections/Owners tab pair so graves can be filtered by owner exactly as they are by section. `app.js` is split into focused files first, so the refactor and the feature stay separable.

**Tech Stack:** Python 3.14, SQLite (stdlib `sqlite3`), pywebview 6.2.1, vanilla HTML/CSS/JS loaded from `file://`.

**Spec:** [docs/superpowers/specs/2026-09-21-grave-owners-design.md](../specs/2026-09-21-grave-owners-design.md)

## Global Constraints

- **This project is not a git repository.** Per-task commits are impossible. Each task therefore ends with a **Checkpoint** step that runs the full suite instead. Do not run `git init` — that is not part of this work.
- Python interpreter is `.venv/Scripts/python.exe`. Always use it; the system Python has no dependencies installed.
- Tests are dependency-free plain-assert scripts run as `python tests/<name>.py`. **Do not introduce pytest** or any new dependency.
- Every query reading owner data uses **`LEFT JOIN owners`**, never an inner join. Owner is optional; an inner join silently hides unowned plots.
- `idx_graves_owner` is **never** created in `schema.sql` — the schema script runs before migrations, when `owner_id` does not yet exist on an existing database.
- Owner name is **unique** (`idx_owners_name`).
- Duplicate owner names merge on **first contact wins**, resolved by lowest `graves.id`.
- `DROP COLUMN` requires SQLite **3.35+**; assert before migrating. Installed version is 3.50.4.
- Before the migration is first run against `data/graveyard.db`, take a timestamped backup.
- The app loads over `file://`: use **plain `<script>` tags, never ES modules** (`import`/`export` are blocked by CORS).
- The JS parameter order in `common` arrays must match the Python signature exactly; these are positional bridge calls.

---

### Task 1: Split `app.js` into focused files

Pure refactor, no behaviour change. The existing suites are the safety net — a passing run before and after is the test.

**Files:**
- Create: `graveyard/web/js/util.js`, `js/api.js`, `js/state.js`, `js/sections.js`, `js/graves.js`, `js/documents.js`
- Modify: `graveyard/web/js/app.js` (reduced to delegation + startup), `graveyard/web/index.html` (script tags)

**Interfaces:**
- Consumes: nothing.
- Produces: the same global functions as today, unchanged in name and signature — `call`, `el`, `$`, `esc`, `debounce`, `toast`, `plural`, `docBadge`, `fileSize`, `show`, `hide`, `closeModalAround`, `confirmDelete`, `state`, `refreshStats`, `refreshSections`, `refreshGraves`, `renderEmptyState`, `refreshAll`, `openSectionModal`, `sectionOptions`, `openGraveModal`, `openDetail`, `renderBurials`, `openDocuments`, `refreshDocuments`, `renderDocuments`, `promptForFirstSection`, `start`.

- [ ] **Step 1: Capture the green baseline**

```bash
cd /c/ClaudeCode/funeral
.venv/Scripts/python.exe tests/test_graves.py
.venv/Scripts/python.exe tests/test_documents.py
```
Expected: `RESULT 8/8 passed` and `RESULT 12/12 passed`. If either fails, stop — do not refactor on a red baseline.

- [ ] **Step 2: Create `js/util.js`**

Move verbatim from `app.js`: `$`, `el` (lines 14-15), and from the Helpers block `plural`, `docBadge`, `fileSize`, `show`, `hide`, `closeModalAround`, `esc`, `debounce`, `toastTimer`, `toast`. Start the file with `"use strict";`.

- [ ] **Step 3: Create `js/api.js`**

Move the `call()` function (lines 3-12) verbatim, including its comment. Start with `"use strict";`.

- [ ] **Step 4: Create `js/state.js`**

Move verbatim: the `let state = {...}` declaration, `refreshStats`, `renderEmptyState`, `refreshAll`, and `confirmDelete`.

Note: `state` is declared with `let` at the top level of a classic script, which places it in the shared global lexical environment — every other script sees it. This is why no modules are needed.

- [ ] **Step 5: Create `js/sections.js`, `js/graves.js`, `js/documents.js`**

- `sections.js`: `refreshSections`, `openSectionModal`, the `sectionForm` submit listener, `promptForFirstSection`.
- `graves.js`: `refreshGraves`, `sectionOptions`, `openGraveModal`, the `graveForm` submit listener, `openDetail`, `renderBurials`, the `burialForm` submit listener.
- `documents.js`: `openDocuments`, `refreshDocuments`, `renderDocuments`, the `uploadDocBtn` listener.

Each starts with `"use strict";`.

- [ ] **Step 6: Reduce `app.js`**

`app.js` keeps only: the global `document.addEventListener("click", ...)` delegation block, the `addSectionBtn` / `addGraveBtn` / `searchInput` / `statusFilter` listeners, `start()`, and the `pywebviewready` bootstrap at the end.

- [ ] **Step 7: Update `index.html` script tags**

Replace the single `<script src="js/app.js"></script>` with, in this order:

```html
  <script src="js/util.js"></script>
  <script src="js/api.js"></script>
  <script src="js/state.js"></script>
  <script src="js/sections.js"></script>
  <script src="js/graves.js"></script>
  <script src="js/documents.js"></script>
  <script src="js/app.js"></script>
```

- [ ] **Step 8: Syntax-check every file**

```bash
for f in graveyard/web/js/*.js; do node --check "$f" || echo "FAILED $f"; done
```
Expected: no `FAILED` lines.

- [ ] **Step 9: Checkpoint — verify no behaviour changed**

Run both Python suites (expect 8/8 and 12/12) and the live-window first-run flow. In the window, confirm: sections list renders, a grave saves, the documents modal opens from a grave row, and the browser console reports no errors. Any difference from Step 1 means the split broke something — fix before continuing.

---

### Task 2: `owners` table, `owner_id`, and the migration

**Files:**
- Create: `tests/test_owners.py`
- Modify: `graveyard/schema.sql`, `graveyard/database.py`

**Interfaces:**
- Consumes: `get_connection`, `init_db` from Task 1's untouched `database.py`.
- Produces: table `owners(id, name, contact, address, notes, created_at, updated_at)`; `graves.owner_id INTEGER REFERENCES owners(id)` nullable; `graves.owner_name` and `graves.owner_contact` removed; index `idx_graves_owner`.

- [ ] **Step 1: Write the failing migration tests**

Create `tests/test_owners.py` following the structure of `tests/test_graves.py` (same `check`/`ok`/`PASS`/`FAIL` harness, same `GRAVEYARD_DB` temp-dir setup before importing `graveyard`). Include the pre-owners schema and these two tests:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

```bash
.venv/Scripts/python.exe tests/test_owners.py
```
Expected: FAIL — `no such table: owners`.

- [ ] **Step 3: Add `owners` to `schema.sql` and move `graves` to its final shape**

Insert the `owners` table **before** `graves` in the file:

```sql
-- Plot owners. A grave is filed under exactly one owner (or none).
CREATE TABLE IF NOT EXISTS owners (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    contact    TEXT NOT NULL DEFAULT '',
    address    TEXT NOT NULL DEFAULT '',
    notes      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_owners_name ON owners(name);
```

In the `graves` definition, delete the `owner_name` and `owner_contact` lines and add:

```sql
    owner_id      INTEGER REFERENCES owners(id),
```

Do **not** add `idx_graves_owner` here (see Global Constraints).

- [ ] **Step 4: Add the migration to `database.py`**

```python
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
```

Then extend `init_db` so the order is schema → column migrations → owners migration → indexes:

```python
def init_db() -> None:
    """Create tables from schema.sql if absent, then bring them up to date."""
    schema = SCHEMA_PATH.read_text(encoding="utf-8")
    with get_connection() as conn:
        conn.executescript(schema)
        _apply_migrations(conn)
        _migrate_owners(conn)
        _ensure_indexes(conn)
```

- [ ] **Step 5: Run to verify it passes**

```bash
.venv/Scripts/python.exe tests/test_owners.py
```
Expected: both migration tests PASS.

- [ ] **Step 6: Checkpoint**

`test_documents.py` must still pass 12/12. `test_graves.py` will now fail where it passes owner text to `create_grave` — that is expected and fixed in Task 4. Note which tests fail so Task 4 can confirm it fixed exactly those.

---

### Task 3: Owner CRUD endpoints

**Files:**
- Modify: `graveyard/api.py`, `tests/test_owners.py`

**Interfaces:**
- Consumes: `owners` table from Task 2.
- Produces: `Api.list_owners(search="")`, `Api.get_owner(owner_id)`, `Api.create_owner(name, contact="", address="", notes="")`, `Api.update_owner(owner_id, name, contact="", address="", notes="")`, `Api.delete_owner(owner_id)`. All return the standard `{ok, data}` / `{ok, error}` envelope. `list_owners` rows carry `grave_count`.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_owners.py`:

```python
def t_owner_crud_round_trip():
    a = _fresh()
    oid = ok(a.create_owner("Aftab Dar", "222-444-777", "1 Main St", "prefers email"))
    o = ok(a.get_owner(oid))
    assert o["name"] == "Aftab Dar" and o["contact"] == "222-444-777", o
    assert o["address"] == "1 Main St" and o["graves"] == [], o
    ok(a.update_owner(oid, "Aftab Dar", "222-444-7777", "2 Main St", ""))
    assert ok(a.get_owner(oid))["contact"] == "222-444-7777"
    ok(a.delete_owner(oid))
    assert ok(a.list_owners()) == []


def t_owner_name_must_be_unique():
    a = _fresh()
    ok(a.create_owner("Aftab Dar"))
    msg = err(a.create_owner("Aftab Dar"))
    assert "already" in msg.lower(), msg


def t_owner_name_required():
    a = _fresh()
    err(a.create_owner("   "))


def t_delete_owner_blocked_while_holding_graves():
    a = _fresh()
    sid = ok(a.create_section("A", "Garden"))
    oid = ok(a.create_owner("Aftab Dar"))
    ok(a.create_grave(sid, "1", "available", oid))
    msg = err(a.delete_owner(oid))
    assert "Aftab Dar" in msg and "1 plot" in msg, msg
    assert len(ok(a.list_owners())) == 1, "owner must survive a refused delete"


def t_delete_owner_allowed_once_empty():
    a = _fresh()
    sid = ok(a.create_section("A", "Garden"))
    oid = ok(a.create_owner("Aftab Dar"))
    gid = ok(a.create_grave(sid, "1", "available", oid))
    ok(a.delete_grave(gid))
    ok(a.delete_owner(oid))


def t_list_owners_reports_grave_count_and_search():
    a = _fresh()
    sid = ok(a.create_section("A", "Garden"))
    oid = ok(a.create_owner("Aftab Dar", "222-444-777"))
    ok(a.create_owner("Margaret Whitfield", "555-0142"))
    ok(a.create_grave(sid, "1", "available", oid))
    ok(a.create_grave(sid, "2", "available", oid))
    rows = {o["name"]: o["grave_count"] for o in ok(a.list_owners())}
    assert rows == {"Aftab Dar": 2, "Margaret Whitfield": 0}, rows
    assert [o["name"] for o in ok(a.list_owners("whitfield"))] == ["Margaret Whitfield"]
```

Add the `_fresh()` helper used above (deletes `DB`, calls `init_db()`, returns `Api()`), and an `err()` helper matching the one in `tests/test_documents.py`.

- [ ] **Step 2: Run to verify it fails**

Expected: FAIL — `'Api' object has no attribute 'create_owner'`.

- [ ] **Step 3: Implement the endpoints**

Add an `# ----- Owners -----` block to `api.py`, placed after the Sections block:

```python
    @_endpoint
    def list_owners(self, search: str = "") -> list[dict]:
        clauses, params = [], []
        if search.strip():
            term = f"%{search.strip()}%"
            clauses.append("(o.name LIKE ? OR o.contact LIKE ?)")
            params.extend([term, term])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with get_connection() as conn:
            return _rows(conn.execute(
                f"""SELECT o.*, (SELECT COUNT(*) FROM graves g WHERE g.owner_id = o.id)
                           AS grave_count
                    FROM owners o {where} ORDER BY o.name""", params))

    @_endpoint
    def get_owner(self, owner_id: int) -> dict:
        with get_connection() as conn:
            owner = conn.execute("SELECT * FROM owners WHERE id = ?", (owner_id,)).fetchone()
            if owner is None:
                raise ValueError("Owner not found.")
            graves = _rows(conn.execute(
                """SELECT g.id, g.plot_number, g.status, s.code AS section_code
                   FROM graves g JOIN sections s ON s.id = g.section_id
                   WHERE g.owner_id = ? ORDER BY s.code, g.plot_number""", (owner_id,)))
        result = dict(owner)
        result["graves"] = graves
        return result

    @_endpoint
    def create_owner(self, name: str, contact: str = "", address: str = "",
                     notes: str = "") -> int:
        name = name.strip()
        if not name:
            raise ValueError("Owner name is required.")
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO owners (name, contact, address, notes) VALUES (?, ?, ?, ?)",
                (name, contact.strip(), address.strip(), notes.strip()))
            return cur.lastrowid

    @_endpoint
    def update_owner(self, owner_id: int, name: str, contact: str = "",
                     address: str = "", notes: str = "") -> bool:
        name = name.strip()
        if not name:
            raise ValueError("Owner name is required.")
        with get_connection() as conn:
            conn.execute(
                """UPDATE owners SET name = ?, contact = ?, address = ?, notes = ?,
                   updated_at = datetime('now') WHERE id = ?""",
                (name, contact.strip(), address.strip(), notes.strip(), owner_id))
        return True

    @_endpoint
    def delete_owner(self, owner_id: int) -> bool:
        with get_connection() as conn:
            owner = conn.execute(
                "SELECT name FROM owners WHERE id = ?", (owner_id,)).fetchone()
            if owner is None:
                raise ValueError("Owner not found.")
            held = conn.execute(
                "SELECT COUNT(*) c FROM graves WHERE owner_id = ?", (owner_id,)
            ).fetchone()["c"]
            if held:
                raise ValueError(
                    f"{owner['name']} still holds {held} "
                    f"plot{'' if held == 1 else 's'}. Reassign them first.")
            conn.execute("DELETE FROM owners WHERE id = ?", (owner_id,))
        return True
```

Add the duplicate-name case to `_friendly_integrity_error`, above its final `return message`:

```python
    if "owners.name" in message:
        return "An owner with that name already exists."
```

- [ ] **Step 4: Run to verify it passes**

Expected: all owner CRUD tests PASS. The grave-related ones still fail until Task 4.

- [ ] **Step 5: Checkpoint**

`test_documents.py` still 12/12.

---

### Task 4: Graves move to `owner_id`

**Files:**
- Modify: `graveyard/api.py`, `tests/test_graves.py`, `tests/test_owners.py`

**Interfaces:**
- Consumes: owner endpoints from Task 3.
- Produces: `create_grave(section_id, plot_number, status="available", owner_id=None, notes="", grave_ref="", deed_id="", date_purchased="")` and `update_grave(grave_id, section_id, plot_number, status, owner_id=None, notes="", grave_ref="", deed_id="", date_purchased="")`. `list_graves(section_id=None, status=None, search="", owner_id=None)` returns rows carrying `owner_name` and `owner_contact` **from the joined owner** (NULL when unassigned).

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_owners.py`:

```python
def t_grave_stores_and_changes_owner():
    a = _fresh()
    sid = ok(a.create_section("A", "Garden"))
    o1 = ok(a.create_owner("Aftab Dar", "222-444-777"))
    o2 = ok(a.create_owner("Margaret Whitfield"))
    gid = ok(a.create_grave(sid, "1", "available", o1))
    g = ok(a.get_grave(gid))
    assert g["owner_id"] == o1 and g["owner_name"] == "Aftab Dar", g
    assert g["owner_contact"] == "222-444-777", g
    ok(a.update_grave(gid, sid, "1", "available", o2))
    assert ok(a.get_grave(gid))["owner_name"] == "Margaret Whitfield"


def t_grave_owner_is_optional():
    a = _fresh()
    sid = ok(a.create_section("A", "Garden"))
    gid = ok(a.create_grave(sid, "1"))
    g = ok(a.get_grave(gid))
    assert g["owner_id"] is None and g["owner_name"] is None, g


def t_unowned_graves_still_listed():
    """A LEFT JOIN regression guard: an inner join would hide this row."""
    a = _fresh()
    sid = ok(a.create_section("A", "Garden"))
    ok(a.create_grave(sid, "1"))
    assert len(ok(a.list_graves())) == 1, "unowned grave vanished from the list"


def t_list_graves_filters_by_owner_and_searches_owner_name():
    a = _fresh()
    sid = ok(a.create_section("A", "Garden"))
    oid = ok(a.create_owner("Aftab Dar"))
    ok(a.create_grave(sid, "1", "available", oid))
    ok(a.create_grave(sid, "2"))
    assert len(ok(a.list_graves(None, "", "", oid))) == 1
    found = ok(a.list_graves(None, "", "Aftab"))
    assert len(found) == 1 and found[0]["plot_number"] == "1", found
```

- [ ] **Step 2: Update `tests/test_graves.py` for the new signature**

Every `create_grave` / `update_grave` call passing owner text moves to `owner_id`. Concretely, in `t_new_fields_round_trip` replace:

```python
    gid = ok(a.create_grave(sid, "1", "reserved", "M. Whitfield", "555-0142",
                            "Family plot", "GRV-00412", "DEED-77", "2019-04-02"))
```
with:
```python
    oid = ok(a.create_owner("M. Whitfield", "555-0142"))
    gid = ok(a.create_grave(sid, "1", "reserved", oid,
                            "Family plot", "GRV-00412", "DEED-77", "2019-04-02"))
```

Apply the same shape to `t_update_changes_new_fields`, `t_list_graves_exposes_new_fields`, `t_search_matches_grave_ref` and `t_search_matches_deed_id` — each drops one positional argument, replacing the two owner strings with a single `owner_id` (or `None`).

In `t_migration_adds_columns_and_keeps_rows`, the `OLD_SCHEMA` insert still writes `owner_name` (that is the point of the test), but the assertion `g["owner_name"] == "Existing Owner"` must become:

```python
    assert g["owner_name"] == "Existing Owner", g   # now supplied by the owners join
```
which holds because the owners migration converts that text into an owner record.

- [ ] **Step 3: Run to verify it fails**

Expected: FAIL — `create_grave` still expects `owner_name`, and `list_graves` has no `owner_id` parameter.

- [ ] **Step 4: Update the grave endpoints**

In `create_grave`, replace the `owner_name`/`owner_contact` parameters and their INSERT columns:

```python
    @_endpoint
    def create_grave(self, section_id, plot_number, status="available",
                     owner_id=None, notes="", grave_ref="", deed_id="",
                     date_purchased="") -> int:
        if not str(plot_number).strip():
            raise ValueError("Plot number is required.")
        with get_connection() as conn:
            _require_section(conn, section_id)
            cur = conn.execute(
                """INSERT INTO graves
                   (section_id, plot_number, status, owner_id,
                    notes, grave_ref, deed_id, date_purchased)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (section_id, str(plot_number).strip(), status, _owner_or_none(owner_id),
                 notes.strip(), grave_ref.strip(), deed_id.strip(),
                 date_purchased.strip()))
            return cur.lastrowid
```

`update_grave` changes the same way, with `owner_id = ?` in the SET list in place of `owner_name` and `owner_contact`.

Add this helper beside `_require_owner`:

```python
def _owner_or_none(owner_id):
    """The dropdown sends "" for an unassigned owner; store NULL."""
    return int(owner_id) if owner_id else None
```

- [ ] **Step 5: Add the join, owner filter and owner search to `list_graves` and `get_grave`**

In `list_graves`, add the filter clause after the `status` clause:

```python
        if owner_id:
            clauses.append("g.owner_id = ?")
            params.append(owner_id)
```

change the signature to `def list_graves(self, section_id=None, status=None, search="", owner_id=None)`, extend the search clause to include the owner name:

```python
            clauses.append("(g.plot_number LIKE ? OR g.grave_ref LIKE ?"
                           " OR g.deed_id LIKE ? OR o.name LIKE ?)")
            params.extend([term, term, term, term])
```

and change the query body to:

```sql
                    SELECT g.*, s.code AS section_code, s.name AS section_name,
                           o.name AS owner_name, o.contact AS owner_contact,
                           (SELECT COUNT(*) FROM documents d
                             WHERE d.grave_id = g.id) AS doc_count
                    FROM graves g
                    JOIN sections s ON s.id = g.section_id
                    LEFT JOIN owners o ON o.id = g.owner_id
                    {where}
                    ORDER BY s.code, g.plot_number
```

Apply the same `LEFT JOIN owners o ON o.id = g.owner_id` and the same two `o.name` / `o.contact` selected columns to `get_grave`.

- [ ] **Step 6: Run to verify it passes**

```bash
.venv/Scripts/python.exe tests/test_owners.py
.venv/Scripts/python.exe tests/test_graves.py
```
Expected: both fully PASS. These must be exactly the tests noted as failing at the end of Task 2.

- [ ] **Step 7: Checkpoint**

All three Python suites pass: `test_owners.py`, `test_graves.py`, `test_documents.py` (12/12).

---

### Task 5: Owners sidebar tab and owner modal

**Files:**
- Create: `graveyard/web/js/owners.js`
- Modify: `graveyard/web/index.html`, `graveyard/web/css/styles.css`, `js/state.js`, `js/app.js`

**Interfaces:**
- Consumes: `list_owners`, `create_owner`, `update_owner`, `delete_owner` from Task 3; `call`, `el`, `esc`, `toast`, `show`, `hide` from Task 1.
- Produces: globals `refreshOwners()`, `openOwnerModal(owner)`, `setTab(name)`; `state.tab` (`"sections"` | `"owners"`) and `state.ownerId` (number | null).

- [ ] **Step 1: Add the tab markup**

Replace the `.sidebar-head` block and the section list in `index.html` with:

```html
      <div class="sidebar-head">
        <div class="tabs">
          <button class="tab active" data-tab="sections">Sections</button>
          <button class="tab" data-tab="owners">Owners</button>
        </div>
        <button class="btn small" id="addSectionBtn">+ Add</button>
        <button class="btn small" id="addOwnerBtn" hidden>+ Add</button>
      </div>
      <ul class="section-list" id="sectionList"></ul>
      <ul class="section-list" id="ownerList" hidden></ul>
```

- [ ] **Step 2: Add the owner modal markup**

Before the `<div class="toast" ...>` line:

```html
  <div class="modal-backdrop" id="ownerModal" hidden>
    <div class="modal">
      <h3 id="ownerModalTitle">Add Owner</h3>
      <form id="ownerForm">
        <input type="hidden" id="ownerId" />
        <label>Name
          <input type="text" id="ownerName" required placeholder="e.g. Aftab Dar" />
        </label>
        <label>Contact
          <input type="text" id="ownerContact" placeholder="phone or email" />
        </label>
        <label>Address
          <input type="text" id="ownerAddress" />
        </label>
        <label>Notes
          <textarea id="ownerNotes" rows="4"></textarea>
        </label>
        <div class="modal-actions">
          <button type="button" class="btn danger" id="deleteOwnerBtn" hidden>Delete</button>
          <span class="spacer"></span>
          <button type="button" class="btn" data-close>Cancel</button>
          <button type="submit" class="btn primary">Save</button>
        </div>
      </form>
    </div>
  </div>
```

- [ ] **Step 3: Add tab styles**

Append to `styles.css` beside the sidebar rules:

```css
.tabs { display: flex; gap: 4px; }
.tab {
  font: inherit; font-size: 12px; text-transform: uppercase;
  padding: 4px 8px; border: none; border-radius: 6px;
  background: none; color: var(--muted); cursor: pointer;
}
.tab.active { background: #e7f0eb; color: var(--accent); font-weight: 600; }
.modal-actions .spacer { flex: 1; }
```

- [ ] **Step 4: Write `js/owners.js`**

```javascript
"use strict";

async function refreshOwners() {
  const owners = await call("list_owners");
  state.owners = owners;
  // No owners yet: say so and offer the action, matching the grave empty state.
  if (owners.length === 0) {
    el("ownerList").innerHTML = `
      <li class="owner-empty">
        <div class="sec-name">No owners recorded yet</div>
        <div class="sec-meta"><span>Plots can be filed under an owner.</span></div>
        <button class="btn small primary" data-add-owner>Add owner</button>
      </li>`;
    return;
  }
  el("ownerList").innerHTML = `<li class="${state.ownerId === null ? "active" : ""}" data-owner-id="">
      <div class="sec-name">All owners</div>
      <div class="sec-meta"><span>Show every plot</span></div></li>` +
    owners.map((o) => `
    <li class="${state.ownerId === o.id ? "active" : ""}" data-owner-id="${o.id}">
      <button class="btn link sec-edit" data-edit-owner="${o.id}">edit</button>
      <div class="sec-name">${esc(o.name)}</div>
      <div class="sec-meta">
        <span>${plural(o.grave_count, "plot")}</span>
        <span>${esc(o.contact || "")}</span>
      </div>
    </li>`).join("");
}

function openOwnerModal(owner) {
  el("ownerModalTitle").textContent = owner ? "Edit Owner" : "Add Owner";
  el("ownerId").value = owner ? owner.id : "";
  el("ownerName").value = owner ? owner.name : "";
  el("ownerContact").value = owner ? owner.contact || "" : "";
  el("ownerAddress").value = owner ? owner.address || "" : "";
  el("ownerNotes").value = owner ? owner.notes || "" : "";
  el("deleteOwnerBtn").hidden = !owner;
  show("ownerModal");
}

el("ownerForm").addEventListener("submit", async (e) => {
  e.preventDefault();
  const id = el("ownerId").value;
  const args = [el("ownerName").value, el("ownerContact").value,
                el("ownerAddress").value, el("ownerNotes").value];
  let newId = null;
  if (id) await call("update_owner", Number(id), ...args);
  else newId = await call("create_owner", ...args);
  hide("ownerModal");
  toast("Owner saved");
  await refreshOwners();
  // Opened from the grave form: hand the new owner straight back to it.
  // `fillOwnerOptions` arrives in Task 6, so this is guarded — between Task 5
  // and Task 6 the inline path simply does nothing rather than throwing.
  if (newId && state.ownerReturnsToGrave) {
    state.ownerReturnsToGrave = false;
    if (typeof fillOwnerOptions === "function") fillOwnerOptions(newId);
  }
  await refreshAll();
});

el("deleteOwnerBtn").addEventListener("click", async () => {
  const id = Number(el("ownerId").value);
  if (!confirm("Delete this owner?")) return;
  await call("delete_owner", id);   // refused by the API if they hold plots
  hide("ownerModal");
  toast("Owner deleted");
  if (state.ownerId === id) state.ownerId = null;
  await refreshOwners();
  await refreshAll();
});

function setTab(name) {
  state.tab = name;
  document.querySelectorAll(".tab").forEach(
    (t) => t.classList.toggle("active", t.dataset.tab === name));
  el("sectionList").hidden = name !== "sections";
  el("ownerList").hidden = name !== "owners";
  el("addSectionBtn").hidden = name !== "sections";
  el("addOwnerBtn").hidden = name !== "owners";
}
```

- [ ] **Step 5: Extend state and wire the delegation**

In `js/state.js`, add `tab: "sections"`, `ownerId: null`, `owners: []`, `ownerReturnsToGrave: false` to the `state` initialiser, and add `refreshOwners()` to the `Promise.all` in `refreshAll` alongside `refreshStats` and `refreshSections`.

In `js/app.js`, inside the global click handler and **before** the `li[data-id]` block (the same ordering trap the documents buttons hit), add:

```javascript
  if (t.dataset.tab) { setTab(t.dataset.tab); return; }
  if (t.dataset.addOwner !== undefined) { openOwnerModal(null); return; }
  if (t.dataset.editOwner) {
    const o = await call("get_owner", Number(t.dataset.editOwner));
    openOwnerModal(o);
    return;
  }
  const ownerLi = t.closest("li[data-owner-id]");
  if (ownerLi) {
    state.ownerId = ownerLi.dataset.ownerId ? Number(ownerLi.dataset.ownerId) : null;
    state.sectionId = null;   // the two filters are mutually exclusive
    await refreshOwners();
    await refreshSections();
    await refreshGraves();
    return;
  }
```

Selecting a section must clear the owner filter symmetrically — in the existing `li[data-id]` block add `state.ownerId = null;` beside `state.sectionId = ...`, and call `await refreshOwners();` so the highlight clears.

Add the button listener next to `addSectionBtn`:

```javascript
el("addOwnerBtn").addEventListener("click", () => openOwnerModal(null));
```

- [ ] **Step 6: Pass the owner filter to `list_graves`**

In `js/graves.js`, change the `refreshGraves` call to:

```javascript
  const graves = await call("list_graves", state.sectionId, state.status,
                            state.search, state.ownerId);
```

- [ ] **Step 7: Add the script tag**

In `index.html`, add `<script src="js/owners.js"></script>` between `sections.js` and `graves.js`.

- [ ] **Step 8: Verify in the live window**

Syntax-check all JS (`node --check`). Then launch against a throwaway database seeded with two owners and three graves, and confirm: the Owners tab switches the list, the `+ Add` button swaps, selecting an owner filters the table and clears the section highlight, selecting a section clears the owner highlight, editing an owner loads their details, and deleting an owner who holds plots shows the refusal toast naming the count.

- [ ] **Step 9: Checkpoint**

All three Python suites pass; no JS console errors in the live window.

---

### Task 6: Owner dropdown on the grave form, with inline create

**Files:**
- Modify: `graveyard/web/index.html`, `graveyard/web/js/graves.js`

**Interfaces:**
- Consumes: `state.owners` and `openOwnerModal` from Task 5; `create_grave` / `update_grave` from Task 4.
- Produces: global `fillOwnerOptions(selectedId)` — called by `owners.js` after an inline create.

- [ ] **Step 1: Replace the owner fields in the grave form**

In `index.html`, replace the Owner name and Owner contact labels with:

```html
        <label>Owner
          <select id="graveOwnerSelect"></select>
        </label>
```

- [ ] **Step 2: Add `fillOwnerOptions` to `js/graves.js`**

```javascript
/* The trailing "+ New owner…" entry opens the owner modal and returns here
 * with the new owner selected, so grave entry is never interrupted. */
function fillOwnerOptions(selectedId) {
  el("graveOwnerSelect").innerHTML =
    `<option value="">— no owner —</option>` +
    state.owners.map((o) =>
      `<option value="${o.id}" ${o.id === selectedId ? "selected" : ""}>${esc(o.name)}</option>`
    ).join("") +
    `<option value="__new">+ New owner…</option>`;
  el("graveOwnerSelect").value = selectedId ? String(selectedId) : "";
}

el("graveOwnerSelect").addEventListener("change", (e) => {
  if (e.target.value !== "__new") return;
  e.target.value = "";               // never leave the sentinel selected
  state.ownerReturnsToGrave = true;
  openOwnerModal(null);
});
```

- [ ] **Step 3: Populate it when the grave modal opens**

In `openGraveModal`, replace the two lines setting `graveOwner` and `graveContact` with:

```javascript
  await refreshOwners();             // never offer a stale or deleted owner
  fillOwnerOptions(grave ? grave.owner_id : null);
```

- [ ] **Step 4: Send `owner_id` on submit**

In the `graveForm` submit listener, change the `common` array so its order matches `create_grave` / `update_grave` exactly:

```javascript
  // Order must match create_grave / update_grave in api.py.
  const common = [
    el("gravePlot").value,
    el("graveStatus").value,
    el("graveOwnerSelect").value,     // "" means unassigned -> NULL
    el("graveNotes").value,
    el("graveRef").value,
    el("graveDeed").value,
    el("gravePurchased").value,
  ];
```

- [ ] **Step 5: Verify in the live window**

Confirm: the dropdown lists existing owners, `— no owner —` saves an unassigned plot, choosing `+ New owner…` opens the owner modal and returns with the new owner selected, the grave saves under that owner, and reopening the grave for edit shows the owner preselected.

- [ ] **Step 6: Checkpoint**

All three Python suites pass; no JS console errors.

---

### Task 7: Owner column in the grave table and detail modal

**Files:**
- Modify: `graveyard/web/index.html`, `graveyard/web/js/graves.js`

**Interfaces:**
- Consumes: `owner_name` / `owner_contact` supplied by the `list_graves` and `get_grave` joins from Task 4.
- Produces: nothing new.

- [ ] **Step 1: Collapse the two table columns into one**

In `index.html`, replace the `<th>Owner</th>` and `<th>Contact</th>` header cells with a single `<th>Owner</th>`.

- [ ] **Step 2: Update the row template**

In `refreshGraves` in `js/graves.js`, replace the two owner cells with one:

```javascript
      <td>${esc(g.owner_name || "—")}</td>
```

- [ ] **Step 3: Show the owner in the detail modal**

In `openDetail`, the existing Owner line already reads `g.owner_name` / `g.owner_contact`, which Task 4 now supplies from the join — confirm it renders the joined values and shows `—` for an unassigned plot.

- [ ] **Step 4: Verify in the live window**

Confirm the table shows one Owner column with the owner's name and `—` for unassigned plots, and that each row's cell count matches the header. The header is now **5 columns**: Section, Plot #, Status, Owner, Actions — down from 6, because Owner and Contact merged. Check no row template still emits a sixth `<td>`.

- [ ] **Step 5: Checkpoint**

All three Python suites pass; run the existing visibility, first-run flow and documents UI live checks.

---

### Task 8: Migrate the live database and update the README

**Files:**
- Modify: `README.md`
- Data: `data/graveyard.db`

**Interfaces:**
- Consumes: everything above.
- Produces: a migrated live database and current documentation.

- [ ] **Step 1: Back up the live database**

```bash
cd /c/ClaudeCode/funeral
cp data/graveyard.db "data/graveyard.backup-$(date +%Y%m%d-%H%M%S).db"
ls -la data/*.db
```

- [ ] **Step 2: Run the migration**

```bash
.venv/Scripts/python.exe -c "
from graveyard.database import init_db, get_connection
init_db()
with get_connection() as c:
    print('graves cols:', [r['name'] for r in c.execute('PRAGMA table_info(graves)')])
    for r in c.execute('''SELECT o.name, o.contact,
                          (SELECT COUNT(*) FROM graves g WHERE g.owner_id=o.id) n
                          FROM owners o ORDER BY o.name'''):
        print(f'  {r[\"name\"]!r} contact={r[\"contact\"]!r} plots={r[\"n\"]}')
    print('unassigned:', c.execute(
        'SELECT COUNT(*) c FROM graves WHERE owner_id IS NULL').fetchone()['c'])
"
```

Expected: `owner_name` and `owner_contact` absent from `graves`; **9 owners**; `Aftab Dar` with contact `222-444-777` holding 2 plots; `unassigned: 3`.

If the counts differ, stop and restore from the Step 1 backup before investigating.

- [ ] **Step 3: Update the README**

- Features: change the Graves bullet so ownership reads as a linked owner record, and add an Owners bullet.
- Architecture tree: add `js/` files from Task 1 and `tests/test_owners.py`.
- Data model table: add an `owners` row; change the `graves` row to list `owner_id` instead of `owner_name` / `owner_contact`.
- Migrations section: note that `init_db()` also runs `_migrate_owners`, which is one-way and drops columns.
- Tests section: add `python tests/test_owners.py`.

- [ ] **Step 4: Final checkpoint**

Run all three Python suites and every live check (visibility, first-run flow, documents UI, owners). Confirm the app opens against the real migrated database with all plots listed and owners populated.

- [ ] **Step 5: Report the two known manual follow-ups**

Tell the project owner explicitly:
1. `Estate of John Whitfield` and `Estate of John Whitfield - 2` are two separate owners; repoint the second plot and delete the spare.
2. `Aftab Dar`'s discarded contact `222-555-7777` is gone from the live data but present in the Step 1 backup if it was the correct number.
