# Grave Owners — Design

**Date:** 2026-09-21
**Status:** awaiting review
**Applies to:** Grave Inventory (pywebview + SQLite desktop app)

## Problem

Ownership is stored as free text on each grave (`graves.owner_name`,
`graves.owner_contact`). Nothing ties two plots to the same person, so the same
owner is retyped per plot and drifts. The live database shows both failure modes:

| Symptom | Evidence in `data/graveyard.db` |
|---|---|
| Same person entered twice, contacts diverge | `Aftab Dar` / `222-444-777` **and** `Aftab Dar` / `222-555-7777` |
| Name suffixed to attach a second plot | `Estate of John Whitfield` and `Estate of John Whitfield - 2` |

Owners become their own records. A grave is filed *under* an owner, and an owner
can hold many graves.

## Decisions

Settled with the project owner before this spec:

1. **One owner per grave.** An owner holds many graves. Joint ownership is
   expressed by naming the estate or family, as the existing data already does.
2. **Duplicate merge keeps the first contact.** `Aftab Dar` becomes one owner
   with `222-555-7777`; `222-444-777` is discarded (the discarded value is
   nine digits and appears to be a typo, while the surviving one is well
   formed).
3. **Owners get their own view**, as a sidebar tab beside Sections, plus inline
   creation from the grave form.
4. **Owner name is unique.** This is the constraint that prevents the duplicate
   recurring. Two genuinely different people sharing a name must be
   disambiguated by the operator (e.g. `John Smith (Jr.)`).

## Scope

**In:** owners table, owner CRUD, owner-filtered grave list, grave form owner
selection with inline create, migration of existing owner text, splitting
`app.js` into several files.

**Out:** multiple owners per grave, merging two existing owners in the UI,
owner-level document attachments, transfer-of-ownership history, and the
outstanding cleanup (`pywebview>=5.0` is still unpinned).

## Step 0 — Split `app.js`

`app.js` is ~440 lines and this feature adds owner rendering and a modal. It is
split **before** the feature is written, and verified against the existing
suites, so the two changes stay separable.

The app loads from `file://`, where ES module imports are blocked by CORS.
Several plain `<script>` tags avoid modules entirely: classic scripts share one
global lexical environment, so a top-level `let` or `function` in one file is
visible to the others. Load order therefore matters only for code that *runs* at
load time, and the only such code is the `addEventListener` calls that touch the
DOM — every script is loaded at the end of `<body>`, after the markup exists.

| File | Holds |
|---|---|
| `js/util.js` | `$`, `el`, `esc`, `debounce`, `toast`, `plural`, `fileSize`, `show`, `hide`, `closeModalAround` |
| `js/api.js` | `call()` — the `{ok, data / error}` envelope wrapper |
| `js/state.js` | the `state` object, `refreshStats`, `refreshAll`, `renderEmptyState` |
| `js/sections.js` | section list rendering, section modal |
| `js/owners.js` | owner list rendering, owner modal *(new in step 2)* |
| `js/graves.js` | grave table, grave modal, grave detail modal |
| `js/documents.js` | documents modal |
| `js/app.js` | global click delegation, toolbar listeners, startup |

No behaviour changes in this step. Success = every existing suite passes
unchanged.

## Data model

### New table

```sql
CREATE TABLE IF NOT EXISTS owners (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    name       TEXT NOT NULL,
    contact    TEXT NOT NULL DEFAULT '',
    address    TEXT NOT NULL DEFAULT '',
    notes      TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_owners_name ON owners(name);
```

`idx_graves_owner ON graves(owner_id)` is deliberately **not** in `schema.sql`.
`init_db()` runs the schema script *before* migrations, and on an existing
database `owner_id` does not exist yet, so the index creation would fail and
abort startup. It is created at the end of the migration step instead, where the
column is guaranteed to exist — for fresh and migrated databases alike.

`contact` stays a single free-text field. The existing values are irregular
(`next-of-kin: 555-0177`, `acosta.fam@example.com 222-444-6666`); parsing them
into phone/email columns would lose information. `address` and `notes` are new
and optional.

### Changed table

`graves` gains `owner_id INTEGER REFERENCES owners(id)`, nullable — three plots
currently have no owner and must stay that way.

`graves` **loses** `owner_name` and `owner_contact`. They are dropped rather than
left in place for a concrete reason: `list_graves` selects `g.*` and joins the
owner, so a surviving `owner_name` column would collide with the joined owner
name in the same result set.

In `schema.sql` the `graves` definition is updated to its final shape — with
`owner_id`, without `owner_name` / `owner_contact` — so a **fresh** database is
created correct and the migration is a no-op on it. The migration exists only to
bring *existing* databases to that same shape.

Every query reading owner data uses a **`LEFT JOIN owners`**, never an inner
join. Owner is optional, and an inner join would silently hide the three
unassigned plots from the grave list, the search and the dashboard counts.

## Migration

The first migration that moves data and drops columns. `database.py` currently
only adds missing columns; it gains an ordered step that runs inside the same
`init_db()` transaction.

1. Create `owners` (from `schema.sql`).
2. `ALTER TABLE graves ADD COLUMN owner_id INTEGER REFERENCES owners(id)`.
3. Backfill, ordered by `graves.id` so "first contact wins" is deterministic:
   for each distinct `TRIM(owner_name)` that is non-empty, insert one owner using
   the contact from the lowest-id grave carrying that name, then set `owner_id`
   on every grave with that name.
4. `ALTER TABLE graves DROP COLUMN owner_name` and `DROP COLUMN owner_contact`.
5. `CREATE INDEX IF NOT EXISTS idx_graves_owner ON graves(owner_id)` — here
   rather than in `schema.sql`, for the ordering reason given above.

**Idempotency:** the whole step is skipped when `graves.owner_id` already exists.

**Safety:** a timestamped copy of `data/graveyard.db` is taken before the
migration is first run against live data. `DROP COLUMN` requires SQLite 3.35+;
the bundled SQLite is well past that, and the version is asserted before the
migration begins so an old runtime fails loudly rather than halfway through.

**Expected result on the live database:** 9 owners; `Aftab Dar` merged onto
`222-555-7777`; 3 graves left unassigned. `Estate of John Whitfield` and
`Estate of John Whitfield - 2` remain two owners — the migration cannot know they
are the same estate, and merging them is a manual follow-up the new UI enables.

## API

| Method | Returns |
|---|---|
| `list_owners(search="")` | owners with `grave_count`, ordered by name |
| `get_owner(owner_id)` | owner plus their graves |
| `create_owner(name, contact, address, notes)` | new id |
| `update_owner(owner_id, name, contact, address, notes)` | `True` |
| `delete_owner(owner_id)` | `True`, or refuses (below) |

`create_grave` and `update_grave` replace their `owner_name`, `owner_contact`
parameters with a single `owner_id` in the same position. `list_graves` gains an
`owner_id` filter alongside `section_id` and `status`, and its free-text search
extends to the owner's name.

**Deleting an owner that holds graves is refused** with a message naming the
count ("Aftab Dar still holds 2 plots. Reassign them first."), consistent with
the existing delete confirmations. A duplicate name is refused through the
existing `_friendly_integrity_error` path.

## UI

**Sidebar** gains `Sections | Owners` tabs. The Owners tab lists each owner with
their plot count; selecting one filters the grave table to that owner's plots,
exactly as selecting a section does today. `state.sectionId` and `state.ownerId`
are mutually exclusive — choosing one clears the other, so the filter shown in
the sidebar always matches the table.

**Grave form:** Owner name and Owner contact are replaced by one Owner dropdown
listing every owner, plus a `+ New owner…` entry. Choosing it opens the owner
modal; saving there returns to the grave form with the new owner selected, so
entry is never interrupted. Owner may be left unset.

**Grave table:** the Owner and Contact columns collapse into a single Owner
column showing the owner's name, or `—` when unassigned.

**Grave detail modal:** shows owner name and contact, read from the joined owner.

**Empty state:** the Owners tab with no owners shows "No owners recorded yet"
with an Add owner button, matching the existing empty-state pattern.

## Error handling

Unchanged in shape: every endpoint returns `{ok, data}` or `{ok, error}` and the
frontend surfaces errors as a toast. The new failure cases are a duplicate owner
name, deleting an owner that still holds plots, and selecting an owner deleted in
another window — the last reuses the existing "record no longer exists" guard
already used for sections.

## Testing

`tests/test_owners.py`, in the established dependency-free style:

- owner create / list / update / delete round-trip
- duplicate name refused
- delete refused while the owner holds graves, and the message names the count
- delete allowed once the owner holds none
- `create_grave` / `update_grave` store and change `owner_id`
- `list_graves` filters by owner and matches owner name in free-text search
- **migration:** build a database with the pre-owners `graves` shape containing a
  duplicate name with two different contacts and a blank-owner row; run
  `init_db()`; assert one owner per distinct name, first contact kept, every
  grave repointed, the blank-owner grave left `NULL`, and the old columns gone
- migration is idempotent across repeated `init_db()` calls

Existing suites (`test_graves.py`, `test_documents.py`) must pass unchanged,
except where they set owner text on graves — those calls move to `owner_id`.

Live-window checks: sidebar tab switching, filtering by owner, inline owner
creation from the grave form, and the delete refusal.

## Risks

| Risk | Handling |
|---|---|
| Migration drops columns irreversibly | Timestamped backup before first live run; migration runs in one transaction |
| Unique name blocks two real people sharing a name | Operator disambiguates; flagged to the project owner before implementation |
| Old SQLite lacking `DROP COLUMN` | Version asserted before the migration begins |
| Split and feature landing together obscure a regression | Split is step 0, verified against all suites before the feature is written |
