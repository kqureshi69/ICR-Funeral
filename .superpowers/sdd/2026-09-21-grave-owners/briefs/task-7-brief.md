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

