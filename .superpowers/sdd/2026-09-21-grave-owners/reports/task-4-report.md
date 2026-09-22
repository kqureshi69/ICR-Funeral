# Task 4 Report: Graves move to `owner_id`

## What I implemented

In `graveyard/api.py`:

1. Added `_owner_or_none(owner_id)` helper beside `_require_owner`:
   ```python
   def _owner_or_none(owner_id):
       """The dropdown sends "" for an unassigned owner; store NULL."""
       return int(owner_id) if owner_id else None
   ```
2. `create_grave(self, section_id, plot_number, status="available", owner_id=None, notes="", grave_ref="", deed_id="", date_purchased="")` — now inserts `owner_id` (via `_owner_or_none`) instead of `owner_name`/`owner_contact`.
3. `update_grave(self, grave_id, section_id, plot_number, status, owner_id=None, notes="", grave_ref="", deed_id="", date_purchased="")` — same change in the `SET` list.
4. `list_graves(self, section_id=None, status=None, search="", owner_id=None)` — added an `owner_id` equality filter clause, extended the free-text search to include `o.name LIKE ?`, added `LEFT JOIN owners o ON o.id = g.owner_id` and selects `o.name AS owner_name, o.contact AS owner_contact`.
5. `get_grave` — same `LEFT JOIN owners` and the two owner columns added to its `SELECT`.

Both joins use `LEFT JOIN`, never inner, per the global constraint and the `t_unowned_graves_still_listed` regression guard.

## TDD evidence

**RED** — after Step 1 (append 4 new tests to `test_owners.py`) and Step 2 (update `test_graves.py` signatures), before touching `api.py`:

```
.venv/Scripts/python.exe tests/test_owners.py
...
RESULT 6/13 passed
  [FAIL] grave_owner_is_optional: table graves has no column named owner_name
  [FAIL] grave_stores_and_changes_owner: 'int' object has no attribute 'strip'
  [FAIL] list_graves_filters_by_owner_and_searches_owner_name: 'int' object has no attribute 'strip'
  [FAIL] delete_owner_allowed_once_empty / delete_owner_blocked_while_holding_graves /
         list_owners_reports_grave_count_and_search: 'int' object has no attribute 'strip'
  [FAIL] unowned_graves_still_listed: table graves has no column named owner_name

.venv/Scripts/python.exe tests/test_graves.py
RESULT 1/8 passed
  [FAIL] fields_are_optional / new_fields_round_trip / migration_adds_columns_and_keeps_rows /
         update_changes_new_fields: no column named owner_name / KeyError owner_name
  [FAIL] list_graves_exposes_new_fields / search_matches_grave_ref / search_matches_deed_id:
         'NoneType' object has no attribute 'strip' (old code calling owner_name.strip() on None)
```

These are exactly the expected failure modes: old `create_grave`/`update_grave` still treating positional arg 4 as `owner_name` text and calling `.strip()` on an int/None, and the dropped `owner_name`/`owner_contact` columns still being referenced.

**GREEN** — after Step 4/5 (api.py changes):

```
.venv/Scripts/python.exe tests/test_owners.py     -> RESULT 13/13 passed
.venv/Scripts/python.exe tests/test_graves.py     -> RESULT 8/8 passed
.venv/Scripts/python.exe tests/test_documents.py  -> RESULT 12/12 passed
```

Note: the brief's own step 6 said "these must be exactly the tests noted as failing at the end of Task 2," and the top-level success criterion quoted 9/9 for `test_owners.py`; that count predates Step 1 adding 4 new tests to that same file (6 pre-existing pass + 3 pre-existing fail = 9 before Step 1). After appending the 4 new owner/grave tests the file has 13 tests, all passing (13/13) — no test was skipped or altered to force a pass; this is simply the correct total after the brief's own Step 1 addition.

## Final result lines (exact)

```
RESULT 13/13 passed   (tests/test_owners.py)
RESULT 8/8 passed     (tests/test_graves.py)
RESULT 12/12 passed   (tests/test_documents.py)
```

## Test files edited

- `tests/test_owners.py` — appended 4 new test functions verbatim from the brief (`t_grave_stores_and_changes_owner`, `t_grave_owner_is_optional`, `t_unowned_graves_still_listed`, `t_list_graves_filters_by_owner_and_searches_owner_name`), inserted just before the `if __name__ == "__main__":` block. No existing test in this file was modified.
- `tests/test_graves.py` — modified only the `create_grave`/`update_grave` call sites in `t_new_fields_round_trip`, `t_update_changes_new_fields`, `t_list_graves_exposes_new_fields`, `t_search_matches_grave_ref`, `t_search_matches_deed_id` to use `owner_id` (via a new `create_owner` call or `None`) instead of the two owner strings, exactly as the brief specifies. `t_migration_adds_columns_and_keeps_rows`'s assertion (`g["owner_name"] == "Existing Owner"`) was left as-is (already matches the brief's target text) — it now passes via the owners join rather than a raw column. `t_fields_are_optional` and `t_migration_is_idempotent` were untouched (they never passed owner text).
- `tests/test_documents.py` — **not edited**. Confirmed no `owner_name`/`owner_contact` references remain in it; all 11 previously-failing fixtures now pass purely from the `api.py` signature/join changes.

## Files changed

- `C:\ClaudeCode\funeral\graveyard\api.py` — `_owner_or_none` helper; `create_grave`, `update_grave`, `list_graves`, `get_grave` per brief Steps 4-5.
- `C:\ClaudeCode\funeral\tests\test_owners.py` — 4 new tests appended.
- `C:\ClaudeCode\funeral\tests\test_graves.py` — 5 call sites updated to the new signature.

## Self-review

- `create_grave`/`update_grave` parameter orders match the brief exactly, `owner_id` replacing the two owner strings at the same position.
- `_owner_or_none("")` → `None`; `_owner_or_none("3")` → `3` (int); `_owner_or_none(None)` → `None`. Confirmed by `t_grave_owner_is_optional` and the owner-string-free create/update tests passing.
- Both `list_graves` and `get_grave` use `LEFT JOIN owners o ON o.id = g.owner_id` — no inner join anywhere touched.
- Free-text search clause in `list_graves` now covers `g.plot_number`, `g.grave_ref`, `g.deed_id`, and `o.name` (owner name), confirmed by `t_list_graves_filters_by_owner_and_searches_owner_name`.
- Only the tests named in the brief/task description were edited; the three pre-existing Task 3 owner tests (`t_owner_crud_round_trip`, `t_owner_name_must_be_unique`, `t_owner_name_required`) and all of `test_documents.py` are untouched.
- Test output is clean — no warnings, no stray prints, exit code 0 on all three suites.
- `schema.sql` was not touched; `idx_graves_owner` was already out of scope for this task and I made no changes there.

## Concerns

None. All three suites are fully green with no tests altered to force a pass beyond exactly what the brief specified. The only deviation from the task description's literal "9/9" figure for `test_owners.py` is explained above and is expected given Step 1 adds 4 tests to that same file.
