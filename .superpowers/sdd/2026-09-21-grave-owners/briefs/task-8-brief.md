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
