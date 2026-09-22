# SDD ledger — plan: docs/superpowers/plans/2026-09-21-grave-owners.md

Spec: docs/superpowers/specs/2026-09-21-grave-owners-design.md (read)

## Setup rulings

Ruling: execute without git — this project has no repository, and the approved
plan's Global Constraints say "Do not run git init". The skill's sdd-workspace,
task-brief and review-package scripts all abort with "not a git repository", so
they are replaced by .superpowers/sdd/<plan>/sdd.py: snapshots stand in for
commits and `diff -ruN` produces review packages. Cost if wrong: no rollback via
git if a subagent damages the tree — mitigated by a full snapshot taken before
every task dispatch, which is a complete restore point.

Ruling: no isolated worktree (superpowers:using-git-worktrees is unusable without
git). Work happens directly in C:\ClaudeCode\funeral. Cost if wrong: a failed task
touches the live tree — mitigated by the pre-task snapshots above, and by the live
database being migrated only in Task 8, after a backup.

## Pre-flight conflict scan

### Cross-task rows (tasks sharing a file or interface)

| Tasks | Produced vs consumed | Finding |
|---|---|---|
| 1 -> 5,6,7 | T1 creates js/state.js, js/app.js, js/graves.js; T5-T7 edit them | OK — all three exist after T1 |
| 1 -> 5 | T1 writes 7 script tags; T5 inserts owners.js between sections and graves | OK — 8 tags total, order valid |
| 2 -> 3 | owners table -> owner CRUD | OK |
| 2 -> 4 | graves.owner_id -> grave endpoints | OK |
| 2 -> 8 | migration -> live run | OK |
| 3 -> 4 | create_owner -> used by T4 tests | OK |
| 3 -> 5 | list/get/create/update/delete_owner -> owners.js | OK |
| 4 -> 5 | list_graves(owner_id) 4th param -> state.ownerId passed positionally | OK — T5 step 6 passes 4 args in order |
| 4 -> 6 | create_grave(section,plot,status,owner_id,notes,ref,deed,purchased) vs JS common array | OK — verified element by element, incl. update_grave's leading grave_id |
| 4 -> 7 | o.name AS owner_name from LEFT JOIN -> table cell and detail modal | OK |
| 5 -> 6 | owners.js calls fillOwnerOptions(), defined only in T6 | FOUND — guarded with typeof check at plan-review time; between T5 and T6 the inline path no-ops instead of throwing |
| 5 -> 6 | state.ownerReturnsToGrave set in T6, initialised in T5 | OK |

### Per-task self-consistency rows

| Task | Own text vs itself | Finding |
|---|---|---|
| 1 | 6 files created + app.js reduced vs 7 script tags | OK — util, api, state, sections, graves, documents, app |
| 2 | OLD_GRAVES fixture vs current live schema | OK — fixture includes grave_ref/deed_id/date_purchased, matching today's shape |
| 2 | schema.sql final shape vs migration early-return | OK — fresh DB has owner_id so migration no-ops; _ensure_indexes still runs |
| 3 | tests reference _fresh()/err() | OK — step 1 mandates adding both |
| 4 | _owner_or_none used vs defined | OK — defined in step 4 |
| 5 | setTab touches addOwnerBtn | OK — added in step 1 |
| 6 | fillOwnerOptions defined vs called from T5 | OK — see cross-task row |
| 7 | column count after merging Owner+Contact | OK — corrected to 5 during plan self-review |
| 8 | expected migration output vs live data | OK — 9 owners / Aftab Dar 222-444-777 / 3 unassigned, matches the survey run before the spec |

Ruling: the app is intentionally broken between Task 2 and Task 4 — Task 2 drops
graves.owner_name while api.py still writes it, and test_graves.py fails until
Task 4 repairs it. This is sequenced, not a defect; Task 2's checkpoint records
which tests fail so Task 4 can confirm it fixed exactly those. Cost if wrong: a
reviewer mistakes the intermediate red state for a regression — mitigated by
saying so in both task dispatches.

## Progress

Task 1: complete (snapshot task-1-base -> task-1-head, review clean, 0 findings)
  Split app.js (442 lines) into util/api/state/sections/graves/documents + app.
  Reviewer verified all 39 top-level bindings present exactly once, bodies
  byte-identical, load order sound. Tests 8/8 + 12/12 before and after.
  Ruling: the reviewer's "mojibake" observation was a false alarm caused by my
  own review-package tooling decoding `diff` output with the Windows locale.
  Verified all 7 JS files are valid UTF-8 with intact em dashes; fixed sdd.py to
  decode UTF-8 explicitly. Cost if wrong: none — the source files were never
  touched, only my diff rendering.

Task 2: implemented (owners table, owner_id, migration, _ensure_indexes; tests 2/2)
  Ruling: the plan's Task 2 Step 6 claim that "test_documents.py must still pass
  12/12" was WRONG. test_documents.py builds its fixtures with create_grave(),
  which still writes the dropped owner_name column, so it breaks from the same
  single root cause as test_graves.py. Verified myself: all 11 failures carry the
  identical error "table graves has no column named owner_name". This is the
  sequenced intermediate breakage, not a regression, and the implementer was
  right not to touch api.py. Task 4 must restore BOTH suites, not just
  test_graves.py. Cost if wrong: an independent documents regression could hide
  behind this until Task 4 — mitigated by requiring Task 4 to demonstrate 12/12
  explicitly and by the per-failure error match above.

Task 2: review ❌ — 1 Critical, 2 Important, 5 Minor
  Ruling: Critical #1 is a DEFECT IN MY PLAN, not in the implementation. I wrote
  the guard as `if "owner_id" in cols: return`, but ALTER TABLE ADD COLUMN is DDL
  and runs in autocommit under Python's legacy sqlite3 transaction control, so it
  commits OUTSIDE the transaction carrying the backfill and drops. I reproduced it:
  abort mid-migration -> owner_id survives rollback, owner_name still holds the
  data, and every later startup exits at the guard. Silent, permanent, and it
  would erase all ownership data from view the moment Task 4 lands. The spec is
  the binding authority and it requires the migration be idempotent and safe, so
  the plan's guard loses. Fix: key the guard on `owner_name` (transactional state
  — only absent after commit), guard the ADD COLUMN with its own check, and add a
  test that aborts mid-migration and asserts the next init_db() completes it.
  Cost if wrong: a self-healing guard could re-run a migration someone wanted
  skipped — not possible here, since owner_name's absence is exactly "already done".

  Ruling: took the mandated backup NOW rather than at Task 8 (data/graveyard.pre-owners-*.db).
  The reviewer correctly flagged that init_db() is the app's startup path, so the
  user launching the app at any point between here and Task 8 would migrate their
  live records irreversibly with no backup. Cost if wrong: one redundant 60KB file.

Task 2: minor (deferred): ok() helper unused in test_owners.py until Task 3 uses it
Task 2: minor (deferred): no test asserts idx_graves_owner exists
Task 2: minor (deferred): MIN(id) column unaliased though load-bearing for the bare-column rule
Task 2: minor (deferred): `if not cols` branch unreachable after executescript
Task 2: minor (deferred): discarded duplicate contacts are dropped with no record (plan-mandated rule)
Task 2: fix round 1/5 (3 addressed, 0 open — critical guard rekeyed to owner_name,
  TRIM/NULL fixture rows added, idempotency now asserts assignments; snapshots
  task-2-head -> task-2-fix1-head)
Task 2: minor (deferred): the owner-id reuse branch added during the fix has no
  test that crashes mid-loop after >=1 owner insert, so that branch is unexercised
Task 2: complete (snapshot task-2-base -> task-2-fix1-head, review clean after 1 fix round)
  owners table, graves.owner_id, self-healing migration, _ensure_indexes.
  tests/test_owners.py 3/3. test_graves.py and test_documents.py intentionally
  red until Task 4 (single cause: api.py still writes owner_name).
Task 3: complete (snapshot task-3-base -> task-3-head, review clean, 0 Critical/Important)
  Five owner endpoints transcribed verbatim; _friendly_integrity_error gains the
  owners.name case. test_owners.py 6/9 — the 3 failures are the Task 4 boundary
  ('int' object has no attribute 'strip': create_grave still treats arg 4 as
  owner_name). Verified by the controller.
Task 3: minor (deferred): gc.collect() at tests/test_owners.py:67 masks a real
  handle leak in Task 2's self-heal fixture — `with sqlite3.connect(DB) as raw:`
  commits but never closes (same bug class as the production leak fixed earlier).
  One-line fix: close it explicitly, then drop the gc.collect(). Test-only, no
  production impact, currently harmless but makes test order load-bearing.
Task 4: complete (snapshot task-4-base -> task-4-head, review clean, 0 Critical/Important)
  create_grave/update_grave take owner_id; list_graves gains owner filter + owner
  search; both owner reads are LEFT JOIN. Controller verified: owners 13/13,
  graves 8/8, documents 12/12. Test-edit audit found no weakened assertions.
  Resolved the reviewer's ⚠️: graves.js still sends owner strings, but Task 6
  Step 4 replaces that array with graveOwnerSelect.value. Sequenced, not a gap.
  Consequence to carry: saving a grave from the live app is BROKEN until Task 6
  lands (_owner_or_none would get a name string). Task 5's live-window check must
  not treat that as a regression.
Task 4: minor (deferred): _owner_or_none("0") returns 0 rather than None, since
  "0" is a truthy string. Unreachable today (the dropdown sends ""), but a
  one-line guard would make the "empty means unassigned" contract total.
Task 5: complete (snapshot task-5-base -> task-5-head, review clean, 0 Critical/Important)
  Sections|Owners tabs, owner list, owner modal, mutually exclusive filters.
  Controller verified delegation order (owner handlers app.js:63-70 precede
  li[data-id] at :80) and both clear directions. Suites stay 13/13, 8/8, 12/12.
Task 5: minor (deferred): owner save/delete handlers call refreshOwners() and then
  refreshAll() (which calls it again) — one duplicate list_owners round trip per
  save. Plan-mandated by the brief's snippet, not an implementer defect.
Task 5: minor (deferred): .owner-empty list item has no dedicated CSS rule
  Ruling: batching Tasks 6 and 7 into one dispatch. Both are small edits to the
  same two files (index.html, graves.js) in the same shape — owner dropdown, then
  owner column — and a reviewer could not meaningfully accept one and reject the
  other, since Task 7's table column and Task 6's form both depend on Task 4's
  join. Cost if wrong: a finding in one half forces a fix round covering both.
Tasks 6+7: fix round 1/5 (1 addressed, 0 open — ownerReturnsToGrave now cleared on
  both dismissal routes via clearOwnerReturnOnDismiss; save path untouched since
  Save is type=submit and never reaches the click delegation)
Tasks 6+7: complete (snapshot task-67-base -> task-67-fix1-head, review clean after
  1 fix round). Owner dropdown with inline create; table Owner column merged to 5
  cells; detail modal shows joined owner. Controller verified the common array
  maps element-for-element onto create_grave/update_grave, header and row cells
  both 5, no surviving el("graveOwner")/el("graveContact") references.
Tasks 6+7: minor (deferred): fillOwnerOptions mixes markup building with DOM
  mutation, unlike the pure sectionOptions beside it (shape dictated by the brief)

Task 8: BLOCKED on a mismatch — correctly stopped rather than improvising on live data.
  Ruling: the MIGRATION IS RIGHT and my plan's expected value was WRONG. Verified
  against the pre-migration backup: grave id 41 (plot 2) holds 222-555-7777, id 42
  (plot 6) holds 222-444-777. The rule "first contact wins, lowest graves.id"
  therefore keeps 222-555-7777. My pre-spec survey ordered by name, not id, so I
  wrote "keeping 222-444-777" into the option the user selected. The user chose a
  RULE, not a number; the rule ran correctly. Leaving the data as migrated — no
  code change (fitting a tested, deterministic rule to one row would be worse) and
  no data edit (overwriting the surviving value to match my mislabel would actively
  degrade their records: 222-555-7777 is well formed, 222-444-777 is nine digits
  and looks like the typo). Cost if wrong: if the user did specifically want
  222-444-777, it is in data/graveyard.pre-owners-*.db and is now also editable in
  two clicks via the Owners tab this plan just built. Must be surfaced to the user.
  Correction to the plan: Task 8's expected "Aftab Dar / 222-444-777" is wrong;
  the correct expectation is 222-555-7777.
  Note: live DB now has 13 plots (was 11 at plan time) — the user added two more
  while this ran. Owner count 9 and unassigned 3 still match.
Task 8: complete (live DB migrated; README updated; checkpoint green)
  Note: the Task 8 subagent hit an API session rate limit part-way through Step 4
  (resets 1pm ET) after finishing Step 3. Ruling: rather than spawn a replacement
  that would hit the same limit, the controller finished the two remaining items
  directly — a stale schema.sql line in the README tree, and the Step 4 checkpoint.
  This is a documented exception to "never do task work in the controller": the
  work left was verification plus a one-line doc fix, not a review finding.
  Cost if wrong: that small remainder had no independent reviewer; the final
  whole-branch review covers it.
  Checkpoint: owners 13/13, graves 8/8, documents 12/12. Live read-only window
  against data/graveyard.db: 13 plots, header 5 / row cells 5, 9 owners, Owners
  tab switches, err null.

Final whole-branch review: NOT READY — 1 Critical, 3 Important, 7 Minor.
  Critical: graveyard/seed.py never migrated (outside every task's brief) — still
  INSERTs owner_name/owner_contact. Controller reproduced: `python -m graveyard.seed`
  dies with OperationalError. This is README step 3, the documented first-run path.
  Important: data-clear-filters (written in Task 1, before ownerId existed) never
  clears state.ownerId — reachable dead end.
  Important: stale owner_id raises FOREIGN KEY -> mapped to the *section* error
  message, which the spec explicitly asked to cover.
  Important: spec + plan both name 222-444-777 as Aftab Dar's survivor; the live
  data holds 222-555-7777. Plan Task 8 Step 5 would have told the user the exact
  inverse about a real person's phone number.
  All 8 deferred minors triaged as genuinely deferrable; none blocks acceptance.

Final fix wave: complete (snapshot final-fix-base -> final-fix-head).
  All 4 findings ADDRESSED on scoped re-review. seed.py migrated to owners and
  verified idempotent; clear-filters resets ownerId; _require_grave_owner added
  with a stale-owner test; spec + plan corrected on Aftab Dar's contact.
  Final state: owners 14/14, graves 8/8, documents 12/12. Live DB: 13 plots,
  9 owners, 3 unassigned, 10 burials, 2 documents.
  Deferred minor (new): seed.py's BURIALS insert is a plain INSERT, so re-running
  the seeder without --reset duplicates burial rows. Pre-existing, confirmed
  untouched by the fix wave.
  Ruling: NOT deleting this workspace, contrary to the skill's finish step. That
  step's premise is "the git history is the record now" — there is no git here, so
  the ledger, reports and review packages are the ONLY record of what was decided
  and why. Deleting them would destroy it. Left in place for the user to remove.
  Cost if wrong: ~2 MB of scratch files the user may not want.
