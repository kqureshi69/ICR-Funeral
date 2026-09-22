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

