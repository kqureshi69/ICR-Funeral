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

