# Task 2 Report: `owners` table, `graves.owner_id`, and the migration

## Fix round 1 — review response (1 Critical, 2 Important)

The coordinator's review found and personally reproduced a defect in the plan text I had followed
faithfully (guard keyed on `owner_id`), plus two under-tested paths in `tests/test_owners.py`. All
three addressed below; scope stayed to `graveyard/database.py` and `tests/test_owners.py` only —
`graveyard/api.py` untouched, `test_graves.py`/`test_documents.py` still expected to fail with
`table graves has no column named owner_name`.

### Critical 1 — interrupted migration was unrecoverable and silent

**Root cause:** `ALTER TABLE graves ADD COLUMN owner_id` is DDL and, under sqlite3's legacy
transaction handling, commits on its own, outside the transaction carrying the backfill and the two
`DROP COLUMN`s. The old guard (`if "owner_id" in cols: return`) keyed "already migrated" on exactly
that column, so an interrupted run left `owner_id` committed but `owner_name`/backfill/drops rolled
back — and the next `init_db()` saw `owner_id` present, concluded the migration was done, and returned
immediately. Every grave read back as unowned, permanently, with the original ownership text gone
(replaced-in-place by the rolled-back ALTER attempt having nothing to restore from, since the DROP
never ran — so `owner_name` still had the data, but it was never looked at again).

**Fix in `graveyard/database.py` `_migrate_owners`:**
- The "already migrated" guard is now `if not cols or "owner_name" not in cols: return` — keyed on the
  old column's absence, which only becomes true once the whole migration commits. A fresh database
  (which never has `owner_name`) also returns here, unaffected.
- The `ADD COLUMN` call is now separately guarded with `if "owner_id" not in cols:`, so a re-run that
  already has the column (from an interrupted prior run) doesn't fail with "duplicate column name".
- The per-owner insert now does a `SELECT id FROM owners WHERE name = ?` first and reuses that id if
  found, instead of unconditionally `INSERT`ing — so a re-run that already inserted some owners before
  a later crash doesn't violate the unique name index either.
- Did not use an explicit `BEGIN`, per the coordinator's ruling.

**New test** `t_migration_self_heals_after_interrupted_run` in `tests/test_owners.py`: connects through
a `sqlite3.Connection` subclass (via `factory=`, since the built-in type's methods can't be
monkeypatched in place) whose `execute()` raises immediately after the `ALTER TABLE graves ADD COLUMN
owner_id` statement runs, simulating a crash at exactly that point. The test first asserts the crash
really did leave `owner_id` committed while `owner_name` survived the rollback (proving the test
reproduces the bug, not just exercises dead code), then calls `init_db()` again and asserts the
migration completes: two owners created, `owner_id` correctly backfilled (including the dedupe/TRIM
cases), and both old columns gone.

### Important 2 — dedupe/TRIM/NULL paths were untested

`_build_old_db()` now adds three more fixture rows to the existing four: `" Aftab Dar "` (padded
duplicate of the existing "Aftab Dar" pair, plot 5), `"   "` (whitespace-only name, plot 6), and a row
with `owner_name`/`owner_contact` both `NULL` (plot 7, inserted via a separate statement since it can't
go through the `(plot, name, contact)` tuple loop with a `NULL` name). `t_migration_creates_owners_and_dedupes`
now asserts: plot 5 merges into the same owner as plots 1/2 (proving `TRIM` drives the grouping, not
just exact equality), and plots 4, 6, and 7 all stay `owner_id IS NULL` (blank, whitespace-only, and
NULL name are all "no owner", not three different code paths accidentally passing before). Deleting
every `TRIM()` from the migration now fails this test, where it previously didn't.

### Important 3 — idempotency test under-asserted

`t_migration_is_idempotent` now captures `owner_id` per plot and the full `owners` table contents
after the first `init_db()`, runs `init_db()` again, and asserts both are byte-for-byte unchanged (not
just that the owner count is still 2). Nulling `owner_id`, dropping the index, or reinserting owner
rows on the second run would now fail this test.

### Covering tests run

```
.venv/Scripts/python.exe tests/test_owners.py
```
```
  [PASS] migration_creates_owners_and_dedupes
  [PASS] migration_is_idempotent
  [PASS] migration_self_heals_after_interrupted_run
RESULT 3/3 passed
```

**Confirmed no new failures** in the suites expected to still be broken (same root cause as before,
`graveyard/api.py` not yet ported — Task 4's job):

```
.venv/Scripts/python.exe tests/test_documents.py
```
```
  [PASS] docs_dir_follows_db
  [FAIL] attach_all_three_owner_types: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] attach_and_list: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] delete_document_removes_file: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] delete_grave_removes_its_documents: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] delete_preview_counts: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] delete_section_removes_descendant_documents: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] exactly_one_owner_enforced: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] rejects_bad_extension: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] rejects_missing_owner: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] rejects_oversize: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] rejects_unknown_owner_type: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
RESULT 1/12 passed
```
```
.venv/Scripts/python.exe tests/test_graves.py
```
```
  [PASS] migration_is_idempotent
  [FAIL] fields_are_optional: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] list_graves_exposes_new_fields: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] migration_adds_columns_and_keeps_rows: KeyError: 'owner_name'
  [FAIL] new_fields_round_trip: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] search_matches_deed_id: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] search_matches_grave_ref: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] update_changes_new_fields: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
RESULT 1/8 passed
```

Byte-for-byte identical to the failure lists recorded before this fix round — no new failures
introduced.

### Files changed this round

- `C:\ClaudeCode\funeral\graveyard\database.py` (`_migrate_owners`: guard keyed on `owner_name`
  absence instead of `owner_id` presence; `ADD COLUMN` separately guarded; owner insert now
  select-or-insert)
- `C:\ClaudeCode\funeral\tests\test_owners.py` (fixture extended with padded/whitespace/NULL rows;
  stronger idempotency assertions; new self-heal test)

---

## What I implemented

- `graveyard/schema.sql`: added `owners(id, name, contact, address, notes, created_at, updated_at)` with
  `CREATE UNIQUE INDEX idx_owners_name`, placed before `graves`. Replaced `graves.owner_name` /
  `graves.owner_contact` with `owner_id INTEGER REFERENCES owners(id)`. Did **not** add
  `idx_graves_owner` here.
- `graveyard/database.py`: added `_migrate_owners(conn)` (adds `owner_id`, groups old grave rows by
  trimmed `owner_name`, dedupes with "first contact wins" via `MIN(id)` grouping, inserts one
  `owners` row per name, backfills `graves.owner_id`, then drops `owner_name`/`owner_contact`, guarded
  by a SQLite ≥ 3.35 version check) and `_ensure_indexes(conn)` (creates `idx_graves_owner` once
  `owner_id` exists — runs for both fresh and migrated databases). `init_db()` now runs
  schema → `_apply_migrations` → `_migrate_owners` → `_ensure_indexes`, exactly the order specified.
- `tests/test_owners.py` (new): same harness/style as `tests/test_graves.py` — `check`/`ok`/`PASS`/`FAIL`,
  temp-dir `GRAVEYARD_DB` set before importing `graveyard`, `sqlite3` imported for the old-shape
  fixture. Two tests: `t_migration_creates_owners_and_dedupes` and `t_migration_is_idempotent`, verbatim
  from the brief.

## TDD evidence

**RED**

```
.venv/Scripts/python.exe tests/test_owners.py
```
```
  [FAIL] migration_creates_owners_and_dedupes: OperationalError: no such table: owners
  [FAIL] migration_is_idempotent: OperationalError: no such table: owners
RESULT 0/2 passed
```
Expected failure — `owners` table did not exist yet. Matches the brief's Step 2 expectation exactly.

**GREEN**

```
.venv/Scripts/python.exe tests/test_owners.py
```
```
  [PASS] migration_creates_owners_and_dedupes
  [PASS] migration_is_idempotent
RESULT 2/2 passed
```

## `tests/test_documents.py` result — NOT 12/12, see concern below

```
.venv/Scripts/python.exe tests/test_documents.py
```
```
  [PASS] docs_dir_follows_db
  [FAIL] attach_all_three_owner_types: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] attach_and_list: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] delete_document_removes_file: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] delete_grave_removes_its_documents: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] delete_preview_counts: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] delete_section_removes_descendant_documents: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] exactly_one_owner_enforced: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] rejects_bad_extension: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] rejects_missing_owner: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] rejects_oversize: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] rejects_unknown_owner_type: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
RESULT 1/12 passed
```

**Root-cause investigation:** every one of these 11 tests calls `Api().create_grave(...)` as setup
(mostly `create_grave(sid, "1")` with no owner text at all). `graveyard/api.py`'s `create_grave` (and
`update_grave`) build an **unconditional** `INSERT`/`UPDATE` that always writes `owner_name` and
`owner_contact` columns, regardless of whether the caller supplied owner text. Since Task 2 (correctly,
per the brief) drops those two columns from `graves`, *any* call to `create_grave` now raises
`OperationalError: table graves has no column named owner_name` — not just calls that pass owner
values. This is the same root cause as the `test_graves.py` breakage (api.py not yet ported to
`owner_id`), it just also happens to hit `test_documents.py` because that suite's fixtures create
graves via the same `Api.create_grave` path. I did not touch `graveyard/api.py` (out of scope, Task 4's
job), and there is no way to keep `test_documents.py` at 12/12 without either touching `api.py` or
having `test_documents.py` insert graves directly via SQL bypassing the Api layer — both outside this
task's brief. See **Concerns** below; flagging this prominently since the brief predicted 12/12.

## `tests/test_graves.py` — exact failures for Task 4 to confirm fixed

```
.venv/Scripts/python.exe tests/test_graves.py
```
```
  [PASS] migration_is_idempotent
  [FAIL] fields_are_optional: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] list_graves_exposes_new_fields: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] migration_adds_columns_and_keeps_rows: KeyError: 'owner_name'
  [FAIL] new_fields_round_trip: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] search_matches_deed_id: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] search_matches_grave_ref: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
  [FAIL] update_changes_new_fields: AssertionError: expected ok, got error: Unexpected error: table graves has no column named owner_name
RESULT 1/8 passed
```

Only `t_migration_is_idempotent` passes (it just calls `init_db()` twice and checks `grave_ref` appears
once — doesn't touch owner fields). The other 6 fail, all because `graveyard/api.py` still references
the dropped `owner_name`/`owner_contact` columns.

## Files changed

- `C:\ClaudeCode\funeral\graveyard\schema.sql`
- `C:\ClaudeCode\funeral\graveyard\database.py`
- `C:\ClaudeCode\funeral\tests\test_owners.py` (new)

`graveyard/api.py` was **not** touched, per instructions.

## Self-review findings

- **Dedupe correctness:** the `duplicates` query groups by `TRIM(owner_name)` and selects the bare
  `owner_contact` alongside `MIN(id)` in the same aggregate — SQLite resolves bare columns from the row
  that produced the `MIN`, so `contact` is guaranteed to come from the lowest-id row. The fixture's
  Aftab Dar rows (plot 1 id lower, contact `222-444-777`; plot 2 id higher, contact `222-555-7777`)
  confirm this: the test asserts `aftab["contact"] == "222-444-777"`, and it passes.
  Verified by direct GREEN run.
- **Idempotency:** confirmed by test — `_migrate_owners` guards on `"owner_id" in cols` before doing
  anything, so a second `init_db()` call returns immediately without touching `owners` or `graves`.
  Not luck: the column check happens before any INSERT/ALTER.
- **Fresh vs. existing databases:** a brand-new database gets `owner_id` from `schema.sql` directly.
  `_migrate_owners` then sees `owner_id` already in `cols` and returns without altering anything.
  `_ensure_indexes` runs unconditionally afterward and creates `idx_graves_owner` in both the fresh-DB
  and migrated-DB cases, since it only checks for the column's presence, not how it got there. Verified
  by reading the code path — `init_db()` always calls `_ensure_indexes` last.
- **Scope:** confirmed `graveyard/api.py`, UI files, and anything beyond schema/database/tests were
  untouched (only `schema.sql`, `database.py` modified; `test_owners.py` created).
- **Output cleanliness:** no stray warnings in `test_owners.py` output — clean 2/2 pass with no
  deprecation or resource warnings.

## Concerns

1. **`tests/test_documents.py` is not 12/12 after this task**, contrary to the brief's Step 6
   expectation. Root cause: `graveyard/api.py`'s `create_grave`/`update_grave` unconditionally write to
   the now-dropped `owner_name`/`owner_contact` columns even when the caller passes no owner text, so
   every grave-creating fixture in `test_documents.py` breaks too, not just ones passing owner values.
   This is the identical root cause as the `test_graves.py` breakage and is squarely Task 4's fix (port
   `api.py` to `owner_id`). I did not touch `api.py` to preserve the task boundary as instructed. Task 4
   should treat `test_documents.py` returning to 12/12 as part of its own verification, in addition to
   the `test_graves.py` list above.
2. Everything else matches the brief's Step 3/4 code verbatim; no deviations.
