# Task 1 Report: Split `app.js` into focused files

## What I did

Followed the brief's steps 1-9 exactly. Split `graveyard/web/js/app.js` (442 lines) into
seven files, moving every function verbatim (no renames, no signature changes, no reordering
of logic within a moved block). Updated `graveyard/web/index.html` to load the new files in
the required order before `app.js`.

## File-by-file mapping

- **`js/api.js`** (`"use strict";` + `call()`): `call`.
- **`js/util.js`** (`"use strict";`): `$`, `el`, `plural`, `docBadge`, `fileSize`, `show`,
  `hide`, `closeModalAround`, `esc`, `debounce`, `toastTimer`, `toast`.
- **`js/state.js`** (`"use strict";`): `let state = {...}`, `refreshStats`, `renderEmptyState`,
  `refreshAll`, `confirmDelete`.
- **`js/sections.js`** (`"use strict";`): `refreshSections`, `openSectionModal`, the
  `sectionForm` submit listener, `promptForFirstSection`.
- **`js/graves.js`** (`"use strict";`): `refreshGraves`, `sectionOptions`, `openGraveModal`,
  the `graveForm` submit listener, `openDetail`, `renderBurials`, the `burialForm` submit
  listener.
- **`js/documents.js`** (`"use strict";`): `openDocuments`, `refreshDocuments`,
  `renderDocuments`, the `uploadDocBtn` click listener.
- **`js/app.js`** (reduced, `"use strict";` retained): the global `document` click-delegation
  block, `addSectionBtn` / `addGraveBtn` / `searchInput` / `statusFilter` listeners, `start()`,
  and the `pywebviewready` bootstrap.

`graveyard/web/index.html`: replaced the single `<script src="js/app.js"></script>` with the
seven tags in the brief's exact order (util, api, state, sections, graves, documents, app).

## Baseline vs post-split test results

Step 1 baseline (before any changes):
```
.venv/Scripts/python.exe tests/test_graves.py
RESULT 8/8 passed
.venv/Scripts/python.exe tests/test_documents.py
RESULT 12/12 passed
```

Post-split (after all edits):
```
.venv/Scripts/python.exe tests/test_graves.py
RESULT 8/8 passed
.venv/Scripts/python.exe tests/test_documents.py
RESULT 12/12 passed
```
Identical results, both green.

## Syntax check (step 8)

```
for f in graveyard/web/js/*.js; do node --check "$f" || echo "FAILED $f"; done
```
No `FAILED` lines — all 7 files parse cleanly.

## Live-window check (step 9)

Ran the provided script (adjusted only to attach the `window.addEventListener('error', ...)`
listener via `evaluate_js` after the sleep, as instructed) against a fresh temp DB with one
section ("A"/"Garden") and one grave ("1") pre-created via the API:

```
CHECK {"stats":5,"sections":2,"rows":1,"err":null}
```

`stats` (5 stat tiles), `sections` (2 = "All sections" + "A"), `rows` (1 grave row) all
non-zero, `err: null`. Healthy — matches expected first-run rendering with no JS errors.

## Self-review findings

- **Completeness:** Grepped all `function`/`async function` declarations plus the
  `const $`, `const el`, `let state`, `let toastTimer` declarations and all
  `addEventListener` call sites across the new files. Every symbol from the brief's
  "Produces" interface list (`call`, `el`, `$`, `esc`, `debounce`, `toast`, `plural`,
  `docBadge`, `fileSize`, `show`, `hide`, `closeModalAround`, `confirmDelete`, `state`,
  `refreshStats`, `refreshSections`, `refreshGraves`, `renderEmptyState`, `refreshAll`,
  `openSectionModal`, `sectionOptions`, `openGraveModal`, `openDetail`, `renderBurials`,
  `openDocuments`, `refreshDocuments`, `renderDocuments`, `promptForFirstSection`, `start`)
  appears exactly once, in the file the brief assigns it to. No duplicates, nothing dropped.
  All four `addEventListener` calls that aren't the global click delegation (`sectionForm`,
  `graveForm`, `burialForm`, `uploadDocBtn`) landed in their assigned files; the global
  `document` click listener plus the four toolbar/bootstrap listeners stayed in `app.js`.
- **Behaviour:** Every moved block was copied character-for-character from the original
  `app.js` read (including comments, e.g. the "Order must match create_grave / update_grave
  in api.py" note, and the doc comments above `renderEmptyState`, `confirmDelete`, `start`).
  No indentation changes beyond what each file's own top level requires (none, since these
  were already top-level declarations).
- **Load order:** Only `sections.js`, `graves.js`, and `documents.js` (plus `app.js`) run
  code at load time (the `addEventListener` calls to wire up forms/buttons), and each of
  those only references `el`, `call`, `toast`, `state`, etc., which are defined in files
  that load earlier (`util.js`, `api.js`, `state.js`) per the required tag order in
  `index.html`. No forward references at load time.
- **Testing:** Both suites match the step 1 baseline exactly (8/8, 12/12).
- **Discipline:** No renames, no signature changes, no logic reordering, no incidental
  cleanups. `app.js` still starts with `"use strict";`.

## Concerns

None. The split is behaviour-preserving; all verification steps pass.
