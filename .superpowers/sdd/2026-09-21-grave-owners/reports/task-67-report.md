# Task 6 + Task 7 Report — Owner dropdown & Owner column

## Fix round 1 — `state.ownerReturnsToGrave` leak on owner-modal cancel/backdrop dismiss

**Finding:** `state.ownerReturnsToGrave` was set to `true` in `graveyard/web/js/graves.js` when "+ New
owner…" was chosen, but only ever cleared inside the owner-form **save** handler in `owners.js`. Dismissing
the owner modal via Cancel (`data-close`) or a backdrop click went through the generic handlers in `app.js`
/ `util.js`, which only hide the modal and never touch the flag — so a cancelled inline-create left the flag
`true` indefinitely, to be wrongly consumed by the next unrelated owner save anywhere in the app (Owners tab
"Add owner", empty-state button, etc.), causing `fillOwnerOptions` to run against the grave form's select
even though that save had nothing to do with the grave form.

**Fix — `graveyard/web/js/app.js`:** added a small shared helper, used by both dismissal routes in the
global click handler:

```javascript
/* The owner modal can be dismissed (Cancel or backdrop click) instead of
 * saved. Without this, a flag set by "+ New owner..." on the grave form
 * would survive the cancel and get consumed by some later, unrelated owner
 * save elsewhere in the app. Not cleared inside openOwnerModal itself: the
 * grave-form path sets the flag and *then* calls openOwnerModal(null), so
 * clearing on open would wipe the flag it just set. */
function clearOwnerReturnOnDismiss(modal) {
  if (modal && modal.id === "ownerModal") state.ownerReturnsToGrave = false;
}

document.addEventListener("click", async (e) => {
  const t = e.target;

  if (t.dataset.close !== undefined) {
    clearOwnerReturnOnDismiss(t.closest(".modal-backdrop"));
    closeModalAround(t);
    return;
  }
  if (t.classList.contains("modal-backdrop")) {
    clearOwnerReturnOnDismiss(t);
    t.hidden = true;
    return;
  }
  ...
```

Both the Cancel button (routed through `data-close` → `closeModalAround`) and a direct backdrop click are
covered by the same helper, gated on `modal.id === "ownerModal"` so dismissing any *other* modal (section,
grave, detail, documents) is unaffected. `openOwnerModal` itself was left untouched, per the reviewer's
ruling — clearing there would wipe the flag the grave-form path just set before calling it.

No Python touched. `fillOwnerOptions` left exactly as-is (the markup/DOM-mutation mix noted as Minor is out
of scope for this fix).

**Files changed in this round:**
- `C:\ClaudeCode\funeral\graveyard\web\js\app.js`

### Covering checks — exact commands and output

Syntax check:
```
$ node --check graveyard/web/js/app.js
SYNTAX OK
```

Extended live-window script (throwaway `GRAVEYARD_DB` in a temp dir, run via
`.venv/Scripts/python.exe`), exercising all four points from the review:

```
$ .venv/Scripts/python.exe live_check_fix1.py
after +New owner (cancel test)  flag= True
after Cancel  flag= False ownerModalOpen= False err= None
after +New owner (backdrop test) flag= True
after backdrop click  flag= False ownerModalOpen= False err= None
owner created from Owners tab  flag= False graveModalOpen= False err= None
after inline-create returns  flag= False {"graveModalOpen":true,"ownerText":"Roundtrip Owner","err":null}
final saved grave row {"rowText":"A 9 available Roundtrip Owner Docs Burials Edit Delete","err":null}
```

Interpretation, mapped to the four requested checks:
1. **Cancel dismissal**: flag flips `True` on choosing "+ New owner…", then `False` after clicking Cancel
   — confirmed cleared, modal closed, no console error.
2. **Backdrop dismissal**: same sequence via a direct click on the `#ownerModal` backdrop element — flag
   again clears to `False`, modal closes, no error.
3. **Unrelated owner creation undisturbed**: switching to the Owners tab and creating "Tab Owner" via
   `addOwnerBtn` leaves the flag `False` (it was never set on this path) and confirms the grave modal is not
   opened as a side effect (`graveModalOpen: False`) — the earlier leak would have made this fire
   `fillOwnerOptions` against a grave form that was never involved.
4. **Save path still works**: repeating "+ New owner…" → save ("Roundtrip Owner") shows the grave modal
   still open with the new owner selected (`ownerText: "Roundtrip Owner"`), and submitting the grave form
   saves it — the table row shows `"A 9 available Roundtrip Owner ..."`. No regression.

Python suites re-run (no Python was changed; confirming no regression):
```
$ .venv/Scripts/python.exe tests/test_owners.py    → RESULT 13/13 passed
$ .venv/Scripts/python.exe tests/test_graves.py    → RESULT 8/8 passed
$ .venv/Scripts/python.exe tests/test_documents.py → RESULT 12/12 passed
```

All green, matching the pre-fix baseline exactly.

---


## Task 6: Owner dropdown on the grave form, with inline create

**`graveyard/web/index.html`**
- Replaced the `Owner name` / `Owner contact` text-input labels in `#graveForm` with a single:
  ```html
  <label>Owner
    <select id="graveOwnerSelect"></select>
  </label>
  ```

**`graveyard/web/js/graves.js`**
- `openGraveModal`: removed the two lines setting `graveOwner`/`graveContact`; added
  `await refreshOwners();` followed by `fillOwnerOptions(grave ? grave.owner_id : null);` before `show("graveModal")`.
- Added `fillOwnerOptions(selectedId)` — builds the `<option>` list from `state.owners` plus a leading
  "— no owner —" and trailing "+ New owner…" (`value="__new"`) entry, and sets `.value` to the selected id
  (or `""` when none).
- Added the `graveOwnerSelect` `change` listener: when `__new` is chosen it immediately resets the select to
  `""` (so the sentinel can never be submitted), sets `state.ownerReturnsToGrave = true`, and calls
  `openOwnerModal(null)`. `owners.js`'s existing submit handler (Task 5) already calls
  `fillOwnerOptions(newId)` on return — that guarded call is now live.
- `graveForm` submit handler: rebuilt the `common` array to send `owner_id` in the correct position (see
  mapping below), and dropped the old `graveOwner`/`graveContact` reads.

## Task 7: Owner column in the grave table and detail modal

**`graveyard/web/index.html`**
- Grave table header: removed `<th>Contact</th>`, kept a single `<th>Owner</th>`. Header is now 5 columns:
  Section, Plot #, Status, Owner, Actions.

**`graveyard/web/js/graves.js`**
- `refreshGraves` row template: removed the `<td>${esc(g.owner_contact || "—")}</td>` cell, keeping only
  `<td>${esc(g.owner_name || "—")}</td>`. Row now emits exactly 5 `<td>` elements, matching the header.
- `openDetail`: no change needed — it already read `g.owner_name` / `g.owner_contact` (joined by Task 4) and
  renders `"—"` when unassigned; confirmed live below.

Checked for stray `colspan` hardcodes: the only other `colspan` values in `graves.js` (burial table, `5`) and
`documents.js` (doc table, `4`) belong to unrelated tables and were untouched. `state.js`'s `renderEmptyState`
toggles a `<div>`, not a table cell, so it needed no change either. Searched the whole `web/` tree for
`graveOwner`/`graveContact` element ids — only the new `graveOwnerSelect` id remains; no dangling references.

## `common` array → Python signature mapping

`create_grave(section_id, plot_number, status="available", owner_id=None, notes="", grave_ref="", deed_id="", date_purchased="")`
`update_grave(grave_id, section_id, plot_number, status, owner_id=None, notes="", grave_ref="", deed_id="", date_purchased="")`

JS call sites: `call("create_grave", section, ...common)` and `call("update_grave", Number(id), section, ...common)`.

| common[i] | JS source                        | create_grave param | update_grave param |
|-----------|-----------------------------------|---------------------|---------------------|
| (prefix)  | `section` (create) / `Number(id), section` (update) | `section_id`        | `grave_id, section_id` |
| 0         | `el("gravePlot").value`           | `plot_number`        | `plot_number`        |
| 1         | `el("graveStatus").value`         | `status`              | `status`              |
| 2         | `el("graveOwnerSelect").value`    | `owner_id`            | `owner_id`            |
| 3         | `el("graveNotes").value`          | `notes`               | `notes`               |
| 4         | `el("graveRef").value`            | `grave_ref`           | `grave_ref`           |
| 5         | `el("graveDeed").value`           | `deed_id`             | `deed_id`             |
| 6         | `el("gravePurchased").value`      | `date_purchased`      | `date_purchased`      |

Element-by-element match confirmed against `graveyard/api.py`. `owner_id` is sent as the select's raw string
value; `""` (no owner) coerces via `_owner_or_none` on the Python side to `None`, and a numeric id string
coerces to `int`.

## Live-window verification

Script run via `.venv/Scripts/python.exe` against a throwaway `GRAVEYARD_DB` in a temp dir (never touched
`data/graveyard.db`). Full output (console mangled the em/en-dash glyphs — cosmetic terminal encoding only,
confirmed by reading the raw JS strings, not an app bug):

```
form open        {"graveModal":true,"ownerOpts":["— no owner —","Aftab Dar","+ New owner…"],"ownerVal":"","headerCells":5,"firstRowCells":0,"rowText":"","err":null}
saved with owner {"graveModal":false,"ownerOpts":["— no owner —","Aftab Dar","+ New owner…"],"ownerVal":"1","headerCells":5,"firstRowCells":5,"rowText":"A 1 available Aftab Dar Docs Burials Edit Delete","err":null}
reopened edit    {"graveModal":true,"ownerOpts":["— no owner —","Aftab Dar","+ New owner…"],"ownerVal":"1","headerCells":5,"firstRowCells":5,"rowText":"A 1 available Aftab Dar Docs Burials Edit Delete","err":null}
unset owner      {"rowText":"A 1 available Aftab Dar Docs Burials Edit Delete A 2 available — Docs Burials Edit Delete","err":null}
owner modal open {"ownerModal":true,"graveModalStillOpen":true,"sentinelCleared":""}
returned to grave{"graveModalOpen":true,"ownerVal":"2","ownerText":"New Owner X","err":null}
```

Interpretation:
- `err` stayed `null` throughout — no console errors.
- `ownerOpts` shows the no-owner entry, "Aftab Dar", and the new-owner sentinel entry, exactly as designed.
- After saving with an owner: `headerCells` and `firstRowCells` are both **5**; the row shows the owner's
  name ("Aftab Dar").
- Reopening for edit: `ownerVal` is `"1"`, the created owner's id — correctly preselected.
- **Unset-owner check**: a second grave saved with the select left at `""` shows `—` in its owner cell
  (`"A 2 available — Docs..."`), i.e. stored as unassigned.
- **Inline-create check**: selecting `+ New owner…` clears the sentinel (`sentinelCleared:""`), opens the
  owner modal while the grave modal stays open behind it (`graveModalStillOpen:true`), and after saving the
  new owner ("New Owner X") the grave modal remains open with `graveOwnerSelect` now set to the new owner's
  id (`"2"`) and its label showing the new name — confirming the round trip back into the grave form works.

## Python suite results

```
tests/test_owners.py     RESULT 13/13 passed
tests/test_graves.py     RESULT 8/8 passed
tests/test_documents.py  RESULT 12/12 passed
```
No Python files were touched, so these numbers are exactly the pre-existing baseline — no regression.

`node --check` passed clean for both modified JS files (`graves.js`, `owners.js` — owners.js was read only,
not edited, checked anyway since it interacts with the new function).

## Files changed

- `C:\ClaudeCode\funeral\graveyard\web\index.html`
- `C:\ClaudeCode\funeral\graveyard\web\js\graves.js`

(`graveyard/web/js/owners.js` was read for context but not modified — its Task-5 guarded call to
`fillOwnerOptions` now resolves against the function defined in this task.)

## Self-review

- `common` array checked element-by-element against `create_grave`/`update_grave` signatures — matches
  (table above).
- `__new` sentinel: the `change` listener resets `e.target.value = ""` synchronously, before opening the
  owner modal, so it can never reach the submit handler. Confirmed live (`sentinelCleared:""`).
- `fillOwnerOptions` preselects correctly for an existing grave (`ownerVal:"1"` on reopen) and defaults to
  `""` (no-owner option) for a new/unassigned grave (verified via the unset-owner check showing `—`).
- Searched the whole `web/` tree for `graveOwner`/`graveContact` element ids: none remain except the new
  `graveOwnerSelect`. No dangling `el(...)` calls that would throw.
- Header (`5`) and first-row (`5`) cell counts match, confirmed live after a save.
- Detail modal (`openDetail`) already read the joined `owner_name`/`owner_contact` fields from Task 4 and
  needed no change; not separately screenshotted but its template is unchanged and those fields are supplied
  by the same `get_grave` join exercised by the Python suite (`grave_owner_is_optional`,
  `grave_stores_and_changes_owner` tests in `test_owners.py`).
- Test output is pristine — no unexpected failures or warnings, 33/33 across the three suites.

## Concerns

None. Grave saving from the live UI, which was broken prior to this task (old `graveOwner`/`graveContact`
fields no longer matching the `owner_id`-based Python signature), is confirmed fixed end-to-end, including
the unassigned-owner path and the inline owner-creation round trip.
