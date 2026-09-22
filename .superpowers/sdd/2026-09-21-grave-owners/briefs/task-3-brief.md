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

