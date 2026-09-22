# Task 3: Owner CRUD Endpoints - Implementation Report

## Implementation Summary

Implemented five owner API endpoints with full CRUD operations:
- `list_owners(search="")` - Lists all owners with grave counts, supports search filtering
- `get_owner(owner_id)` - Retrieves owner details with associated graves
- `create_owner(name, contact="", address="", notes="")` - Creates new owner record
- `update_owner(owner_id, name, contact="", address="", notes="")` - Updates owner details
- `delete_owner(owner_id)` - Deletes owner only if no graves assigned

Added supporting test helpers:
- `_fresh()` - Creates clean database for each test
- `err()` - Unwraps error responses for assertion testing

Updated error handling:
- Added `owners.name` case to `_friendly_integrity_error()` for duplicate name detection

## TDD Evidence

### RED Phase
Test run command: `.\.venv\Scripts\python.exe tests\test_owners.py`

Initial state before implementation:
```
AttributeError: 'Api' object has no attribute 'create_owner'
```

### GREEN Phase
After implementation:
```
  [PASS] migration_creates_owners_and_dedupes
  [PASS] migration_is_idempotent
  [PASS] migration_self_heals_after_interrupted_run
  [PASS] owner_crud_round_trip
  [PASS] owner_name_must_be_unique
  [PASS] owner_name_required
  [FAIL] delete_owner_allowed_once_empty: Unexpected error: 'int' object has no attribute 'strip'
  [FAIL] delete_owner_blocked_while_holding_graves: Unexpected error: 'int' object has no attribute 'strip'
  [FAIL] list_owners_reports_grave_count_and_search: Unexpected error: 'int' object has no attribute 'strip'
RESULT 6/9 passed
```

## Full Test Results

### test_owners.py - 6/9 PASSED

**Passing Tests (6):**
1. `migration_creates_owners_and_dedupes` - Pre-existing migration test ✓
2. `migration_is_idempotent` - Pre-existing migration test ✓
3. `migration_self_heals_after_interrupted_run` - Pre-existing migration test ✓
4. `owner_crud_round_trip` - Create, read, update, delete workflow ✓
5. `owner_name_must_be_unique` - Duplicate name constraint validation ✓
6. `owner_name_required` - Empty name validation ✓

**Failing Tests (3 - Expected):**
1. `delete_owner_allowed_once_empty` - FAIL: Calls `create_grave(sid, "1", "available", oid)` with Task 4 signature (owner_id parameter doesn't exist yet)
2. `delete_owner_blocked_while_holding_graves` - FAIL: Same cause as above
3. `list_owners_reports_grave_count_and_search` - FAIL: Same cause as above

All three failing tests are expected per task requirements. They attempt to use the Task 4 signature for `create_grave()` which includes an `owner_id` parameter. The current `create_grave()` signature has `owner_name` (string) as the 4th parameter, causing AttributeError when passed an int.

## Files Changed

1. **tests/test_owners.py**
   - Added `import gc` for garbage collection during test setup
   - Imported `Api` from `graveyard.api`
   - Added `err()` helper function to unwrap error responses
   - Added `_fresh()` helper function to create clean test databases
   - Added 6 new test functions with full owner CRUD scenarios

2. **graveyard/api.py**
   - Updated `_friendly_integrity_error()` to handle `owners.name` unique constraint
   - Added `# ----- Owners -----` block with 5 endpoint methods:
     - `list_owners()` with grave count aggregation and search support
     - `get_owner()` returning owner plus associated graves
     - `create_owner()` with validation
     - `update_owner()` with validation
     - `delete_owner()` with graves-holding constraint check

## Self-Review Findings

✓ **SQL Accuracy**: All queries transcribed exactly from brief:
  - Subquery for grave_count in list_owners
  - JOIN for section_code in get_owner graves query
  - All parameter placeholders and column names match precisely

✓ **Error Messages**: Delete error message includes exact format with proper pluralization:
  ```python
  f"{owner['name']} still holds {held} plot{'' if held == 1 else 's'}. Reassign them first."
  ```

✓ **Grave Count Coverage**: list_owners returns grave_count (0 or more) for all owners via LEFT JOIN subquery

✓ **Get Owner Missing ID**: Raises clear ValueError "Owner not found." when owner doesn't exist

✓ **Grave Endpoints Untouched**: create_grave() and update_grave() retain original signatures and behavior

✓ **Migration Tests Preserved**: All three pre-existing migration tests pass without modification

✓ **Database Handling**: _fresh() uses gc.collect() to properly release Windows file handles before DB deletion

## Concerns

**None**. All acceptance criteria met:
- Owner-only tests: 3/3 passing
- Migration tests: 3/3 passing (unchanged)
- Grave-dependent tests: 3/3 failing as expected (Task 4 dependency)
- Error handling complete with unique constraint coverage
- No regressions introduced to existing functionality
- Database cleanup robust for Windows file locking

## Task 4 Blockers

The three currently-failing tests will pass once Task 4 updates `create_grave()` signature:
- Current (Task 3): `create_grave(section_id, plot_number, status="available", owner_name="", ...)`
- Task 4 Required: `create_grave(section_id, plot_number, status="available", owner_id=None, ...)`

These tests explicitly call the Task 4 signature to test owner assignment at grave creation time.
