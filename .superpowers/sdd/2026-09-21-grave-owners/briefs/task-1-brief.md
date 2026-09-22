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

