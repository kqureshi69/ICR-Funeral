# Final whole-branch review fixes — report

Date: 2026-09-21
Scope: fix all four findings from the final whole-branch code review of the
grave-owners work. No git operations performed (project is not a git repo).
`data/graveyard.db` was never touched — every Python run used a temp
`GRAVEYARD_DB` set before importing `graveyard`.

## Finding 1 (Critical) — `graveyard/seed.py` writes dropped columns

File: `graveyard/seed.py`

- Added a module-level `OWNERS` list of `(name, contact)` pairs, one entry
  per distinct owner in the existing seed data, including
  `Estate of John Whitfield` and `Estate of John Whitfield - 2` as two
  separate owners (owner names are unique, so keeping the original identical
  name for both would have collapsed them into one owner — renaming the
  second preserves the "two separate owners" intent from the spec).
- `GRAVES` tuples shrank from
  `(section_code, plot_number, status, owner_name, owner_contact, notes)` to
  `(section_code, plot_number, status, owner_name, notes)`, with `None` for
  the three unowned plots (A-4, B-11, C-V-2).
- `seed()` now inserts `OWNERS` right after `SECTIONS`, using
  `INSERT OR IGNORE INTO owners (name, contact)` and resolving each name to
  an id with the same `cur.lastrowid or SELECT id ...` pattern already used
  for `section_ids` — no new resolution pattern introduced.
- The grave insert now writes `owner_id` (resolved from the name via
  `owner_ids[owner]`, or `None` when `owner` is falsy) instead of
  `owner_name`/`owner_contact`.
- `--reset`'s `executescript` gained `DELETE FROM owners;`, placed after
  `DELETE FROM graves;` (graves references owners, so graves must go first)
  and before `DELETE FROM sections;` (order between owners/sections doesn't
  matter, since owners doesn't reference sections).

### Seeder verification (throwaway DB, `GRAVEYARD_DB` set to a temp file)

Ran `python -m graveyard.seed` twice, then `--reset` once more.

Two-run-without-reset result (idempotent for owners/graves as required):
```
owners: 6 rows — Estate of John Whitfield, Estate of John Whitfield - 2,
                 Margaret Whitfield, Acosta Family, Daniel Okoro,
                 Sgt. Harold Bain (ret.)   (contacts all intact)
graves: 9 rows, owner assignments exactly matching the original seed data;
        A-4, B-11, C-V-2 unowned (None)
counts: 6 owners, 9 graves
```
Note (pre-existing, out of scope): the `BURIALS` insert loop uses a plain
`INSERT` (no `OR IGNORE`), so running the seeder twice without `--reset`
duplicates burial rows (8 instead of 4). This is unchanged, unrelated
pre-existing behavior — not part of the four assigned findings — and I left
it alone.

`--reset` result: 6 owners, 9 graves, 4 burials, 3 sections — a clean
rebuild with owner ids starting fresh (13-18, confirming the prior rows were
actually deleted) and all owner names/contacts/assignments matching the
original seed data.

## Finding 2 (Important) — "Clear filters" leaves `ownerId` set

File: `graveyard/web/js/app.js`, `data-clear-filters` branch.

Added `state.ownerId = null;` beside `state.sectionId = null;`, and
`await refreshOwners();` beside `await refreshSections();`, matching the
existing pattern used when an owner is picked from the sidebar (lines
~88-95, which reset `state.sectionId` and refresh both lists). Verified with
`node --check graveyard/web/js/app.js` (passes).

## Finding 3 (Important) — stale owner reports a section error

File: `graveyard/api.py`

- Added `_require_grave_owner(conn, owner_id)`: no-ops when `owner_id` is
  falsy, otherwise raises
  `ValueError("The selected owner no longer exists. Reopen the form and choose an owner.")`
  if the `owners` row doesn't exist. Named distinctly from the existing
  `_require_owner(conn, owner_type, owner_id)` (which validates a
  *document's* parent record — section/grave/burial) to avoid overloading or
  shadowing it, per the finding's explicit naming instruction. A docstring
  on the new helper cross-references `_require_owner` to make the
  distinction explicit for future readers.
- Called `_require_grave_owner(conn, owner_id)` right after
  `_require_section(conn, section_id)` in both `create_grave` and
  `update_grave`.
- Did not touch `_require_owner`, `_friendly_integrity_error`, or any other
  deferred-cleanup item.

### New test

`tests/test_owners.py::t_update_grave_with_stale_owner_reports_owner_not_section`

- Creates a section, an owner, and a grave under that owner.
- Deletes the owner's row directly via a raw `sqlite3.connect(DB)` connection
  (bypassing `delete_owner`, which would refuse, and bypassing
  `get_connection`, which turns `PRAGMA foreign_keys` on and would otherwise
  block the delete since a grave still references the owner).
- Calls `update_grave` with the now-stale `owner_id` and asserts the
  returned error message contains "owner" (case-insensitive) and does NOT
  contain "section" — i.e. it's not the old, wrong,
  "selected section no longer exists" message.

## Finding 4 (Important) — spec/plan name the wrong surviving contact

Corrected exactly three passages, data and migration code untouched:

- `docs/superpowers/specs/2026-09-21-grave-owners-design.md`, "Decisions"
  item 2: now says `Aftab Dar` becomes one owner with `222-555-7777`,
  `222-444-777` discarded, with an added parenthetical noting the discarded
  value is nine digits and looks like a typo while the surviving one is well
  formed.
- Same file, "Expected result on the live database" paragraph: now names
  `222-555-7777` as the value `Aftab Dar` was merged onto.
- `docs/superpowers/plans/2026-09-21-grave-owners.md`, Task 8 Step 2's
  "Expected" line: now says `Aftab Dar` holds contact `222-555-7777`.
- Same file, Task 8 Step 5's second follow-up line: now says the discarded
  contact is `222-444-777` (previously said the opposite, matching the
  finding's description of the inverted text).
- Ticked all five Task 8 checkboxes (`- [ ]` → `- [x]`) since that task is
  complete.
- Left the synthetic test-fixture numbers inside the plan's Task 2 example
  code (`tests/test_owners.py`-mirroring blocks, lines ~146, ~169, ~307-481)
  untouched — those are independent, deliberately-authored fixture data for
  exercising "lowest id wins" merge logic, not a restatement of the live-DB
  Aftab Dar finding, and the finding didn't ask for them to change.
- `README.md` does not mention either contact number, so nothing to fix
  there.

## Test suite results

```
tests/test_owners.py    RESULT 14/14 passed   (13 pre-existing + 1 new)
tests/test_graves.py    RESULT 8/8 passed
tests/test_documents.py RESULT 12/12 passed
```
`node --check graveyard/web/js/app.js` — passes, no syntax errors.

## Files changed

- `graveyard/seed.py`
- `graveyard/web/js/app.js`
- `graveyard/api.py`
- `tests/test_owners.py`
- `docs/superpowers/specs/2026-09-21-grave-owners-design.md`
- `docs/superpowers/plans/2026-09-21-grave-owners.md`

## Self-review

- Re-read every edited region after editing (api.py guard placement, both
  call sites; seed.py's owner resolution and delete order; app.js clear
  filters branch; both doc files' corrected passages and checkbox state).
- Confirmed `_require_grave_owner` truly no-ops on `None`/`""`/`0` (all
  falsy) rather than raising, matching `create_grave`/`update_grave`'s
  optional-owner contract exercised by `t_grave_owner_is_optional`.
- Confirmed the new test's raw-connection delete actually succeeds (i.e.
  really exercises the stale-owner path) — verified by the assertion
  passing (an unexpected `IntegrityError` from a blocked delete would have
  surfaced as a different, unrelated failure in `err()`/`ok()`).
- Confirmed no out-of-scope items were touched: `_owner_or_none`,
  `_require_owner`'s name, `gc.collect()`, `MIN(id)`, `fillOwnerOptions`,
  `.owner-empty`, `util.js`'s `$`, and the `setTab` question were all left
  exactly as found.
- Grepped the whole repo for the two contact numbers to confirm no other
  doc/code passage needed correcting (README clean; remaining hits are the
  in-scope-fixed lines and the untouched test-fixture/example-code lines).
- Confirmed the live `data/graveyard.db` file's mtime/backups were
  untouched by listing `data/*.db` after all work — only the pre-existing
  backup files from the real migration are present, no new ones created by
  this session.

## Concerns

None blocking. One observation noted above (not a finding, not fixed,
flagged for visibility only): `seed.py`'s `BURIALS` insert loop was already
a plain `INSERT` before this change, so re-running the seeder without
`--reset` duplicates burial rows. This predates my change, is outside the
four assigned findings, and the seeder's stated idempotency contract in the
review brief was scoped to "owners and graves," which do come out correct
across repeated runs.
