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

