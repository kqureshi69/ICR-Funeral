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

