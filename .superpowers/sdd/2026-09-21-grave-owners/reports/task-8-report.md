# Task 8 Report — Migrate the live database and update the README

## Status: BLOCKED

The migration ran and the database has already been modified (columns dropped,
`owners` table populated). Per the task's explicit stop condition, I did **not**
attempt to repair, re-run, or restore anything after detecting the mismatch below.
README updates (Step 3) were **not** started, since Step 2 must pass first.

## Backup taken (Step 1)

```
data/graveyard.backup-20260921-091048.db
```

(61,440 bytes — identical size to the pre-migration `graveyard.db`, taken
immediately before running `init_db()`.)

Existing backups from earlier in the plan, left untouched:
- `data/graveyard.backup-20260920-184144.db`
- `data/graveyard.pre-owners-20260921-083411.db`

## Pre-migration state (captured before running init_db())

- `graves` columns: `id, section_id, plot_number, status, owner_name, owner_contact, notes, created_at, updated_at, grave_ref, deed_id, date_purchased`
- Plot count: **13** (not 11 — the live db has extra hand-added plots "5" and "6" beyond the original seed data, as flagged in the task context)
- Sections: 4, Burials: 10, Documents: 2
- Raw owner text on graves (relevant rows only):
  - id 41, plot "2": `owner_name='Aftab Dar'`, `owner_contact='222-555-7777'`
  - id 42, plot "6": `owner_name='Aftab Dar'`, `owner_contact='222-444-777'`

## Step 2: Migration run — full verification output (exact)

```
graves cols: ['id', 'section_id', 'plot_number', 'status', 'notes', 'created_at', 'updated_at', 'grave_ref', 'deed_id', 'date_purchased', 'owner_id']
  'Acosta Family' contact='acosta.fam@example.com 222-444-6666' plots=1
  'Aftab Dar' contact='222-555-7777' plots=2
  'Daniel Okoro' contact='555-0199' plots=1
  'Estate of John Whitfield' contact='�' plots=1
  'Estate of John Whitfield - 2' contact='�' plots=1
  'Margaret Whitfield' contact='555-0142' plots=1
  'Mr. XYZ' contact='231-234-5678' plots=1
  'Mrs. ABC' contact='333-444-5555' plots=1
  'Sgt. Harold Bain (ret.)' contact='next-of-kin: 555-0177' plots=1
unassigned: 3
```

## Comparison against expected result

| Check | Expected | Actual | Match |
|---|---|---|---|
| `owner_name`/`owner_contact` absent from `graves` | absent | absent (`graves cols` list has neither) | YES |
| Owner count | 9 | 9 | YES |
| Aftab Dar plot count | 2 | 2 | YES |
| Aftab Dar surviving contact | `222-444-777` | `222-555-7777` | **NO — MISMATCH** |
| Unassigned graves | 3 | 3 | YES |

**The single failing check:** Aftab Dar's surviving contact is `222-555-7777`
(from grave id 41), not the expected `222-444-777` (from grave id 42).

This is consistent with the plan's stated global constraint — "Duplicate owner
names merge on first contact wins, resolved by lowest `graves.id`" — since grave
id 41 < grave id 42, so the migration correctly kept the contact belonging to
the lower id. But the brief's Step 2 expected value says the opposite contact
should survive. Either the implemented merge logic disagrees with the brief's
expected fixture value, or the "lowest id wins" rule itself needs to be "highest
id wins" / some other tiebreak for this to produce `222-444-777`. I did not
attempt to determine which side is correct — that judgment belongs to the
controller.

## Plot / record count integrity (Step 4 partial — record-count checks only)

- Plot count before: 13, after: 13 — all plots survived.
- Sections: 4 → 4 (unchanged)
- Burials: 10 → 10 (unchanged)
- Documents: 2 → 2 (unchanged)
- Full `graves.owner_id` mapping post-migration:

```
id=20 plot='1'  owner_id=4
id=21 plot='2'  owner_id=5
id=22 plot='3'  owner_id=6
id=23 plot='4'  owner_id=None
id=24 plot='10' owner_id=1
id=25 plot='11' owner_id=None
id=26 plot='12' owner_id=3
id=27 plot='V-1' owner_id=9
id=28 plot='V-2' owner_id=None
id=39 plot='5'  owner_id=7
id=40 plot='6'  owner_id=8
id=41 plot='2'  owner_id=2
id=42 plot='6'  owner_id=2
```

owner_id=2 is Aftab Dar (confirmed matches plots=2 above), unassigned ids
23/25/28 correspond to the 3 originally-blank `owner_name` rows — consistent.

## Not performed (blocked by Step 2 mismatch)

- Step 3 (README updates) — not started, per instructions to stop before
  further changes once Step 2 fails.
- Step 4 (full three-suite test run + live-window check) — not run. The
  database is already migrated (irreversible `DROP COLUMN`), so the app and
  test suites would now run against the post-migration schema regardless: I
  chose not to run them further so as to take no additional action beyond
  what's needed to report the blocker clearly, per "do not attempt to repair
  the database... report BLOCKED with the actual output. The controller will
  decide."
- Step 5 (verbal follow-ups) — see below, still applicable regardless of the
  contact-value blocker.

## Known manual follow-ups (Step 5 — still true regardless of blocker)

1. `Estate of John Whitfield` (owner_id=4, grave id 20) and
   `Estate of John Whitfield - 2` (owner_id=5, grave id 21) are two separate
   owners; the project owner should repoint the second plot to the correct
   owner and delete the spare owner record.
2. Aftab Dar's discarded contact is present in the Step 1 backup
   (`data/graveyard.backup-20260921-091048.db`) if it turns out to be the
   correct number — see the mismatch above, which is precisely about which of
   Aftab Dar's two contacts should have survived.

## Self-review

- Verification output quoted exactly as printed, byte-for-byte (including the
  literal `�` replacement character in the Whitfield contacts, which was
  already present pre-migration — not something this task introduced).
- Confirmed no files in `data/` were deleted or moved; only `graveyard.db`
  itself was modified by the migration, and a fresh timestamped backup was
  taken beforehand.
- Did not touch README.md, since Step 3 is gated on Step 2 passing.
- Did not re-run `init_db()` a second time after detecting the mismatch.

## Concerns

- **The database has already been irreversibly migrated** (SQLite
  `DROP COLUMN owner_name`, `DROP COLUMN owner_contact`) as part of running
  Step 2 to get the verification output the brief required. This could not be
  avoided without violating the brief's own Step 2 instructions, which require
  actually running the migration to observe the result. The pre-migration
  state is fully recoverable from `data/graveyard.backup-20260921-091048.db`
  (or either earlier backup) if the controller decides the current merge
  result is wrong and wants to re-derive it differently before re-running.
- The root cause is either: (a) the migration's tie-break implementation does
  not match "first contact wins, resolved by lowest graves.id" as stated in
  the plan's Global Constraints, or (b) it matches that rule correctly but the
  brief's expected fixture value assumed the opposite tiebreak. I have not
  inspected the migration source (`graveyard/database.py` /
  `_migrate_owners`) to determine which, since the task explicitly says not to
  attempt repair — flagging for the controller's decision instead.
