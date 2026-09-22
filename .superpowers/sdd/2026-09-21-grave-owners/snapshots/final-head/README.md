# Grave Inventory

A small desktop application for managing cemetery grave inventory — organised by
**section** and **plot number**, tracking **ownership** and marking graves as
**used** (occupied) with burial records.

Built with **Python + [pywebview](https://pywebview.flowrl.com/) + SQLite**: a
native desktop window hosting an HTML/JS frontend that talks to Python over the
pywebview JS bridge.

---

## Features

- **Sections** — create/edit cemetery sections (code, name, description) with live plot counts.
- **Graves** — add/edit plots per section with a unique plot number, an owner
  linked from the owners list (or created inline), notes, and reference details
  (grave id, deed id, date purchased).
- **Owners** — first-class owner records (name, contact) with their own
  Sections|Owners sidebar tab, so graves can be filtered by owner exactly as
  they are by section; one owner can hold several plots.
- **Status tracking** — every grave is `available`, `reserved`, or `occupied`, shown as colour badges.
- **Mark as used** — recording a burial automatically flips the grave to *occupied*; a grave can hold multiple burial records over time.
- **Filtering** — filter by section, status, and free-text search across plot number, owner, grave id and deed id.
- **Dashboard** — header totals for plots, availability, and section count.
- **Documents** — attach scanned deeds, certificates or site plans to a section, a
  grave or an individual burial; open them in the system's default application.

## Architecture

```
funeral/
├── run.py                  # launcher: `python run.py`
├── requirements.txt
├── graveyard/
│   ├── app.py              # creates the pywebview window, wires the Api
│   ├── api.py              # Api class — every method is callable from JS
│   ├── database.py         # SQLite connection + schema init
│   ├── documents.py        # document store: files on disk beside the database
│   ├── schema.sql          # tables: sections, owners, graves, burials, documents
│   ├── seed.py             # example data loader
│   └── web/                # frontend (served from disk by pywebview)
│       ├── index.html
│       ├── css/styles.css
│       └── js/
│           ├── util.js     # shared helpers
│           ├── api.js      # thin wrapper over window.pywebview.api
│           ├── state.js    # in-memory app state
│           ├── sections.js # sections tab: list, form, filtering
│           ├── owners.js   # owners tab: list, form, inline create
│           ├── graves.js   # graves list/form, owner dropdown
│           ├── documents.js # document attach/list/open
│           └── app.js      # entry point: wires the above together
├── tests/
│   ├── test_documents.py   # `python tests/test_documents.py`
│   ├── test_graves.py      # grave reference fields + schema migration
│   └── test_owners.py      # owners CRUD + owners migration/merge
└── data/
    ├── graveyard.db        # created at first run (git-ignored)
    └── documents/          # uploaded files, named by UUID (git-ignored)
```

**How the layers connect**

- `app.py` calls `init_db()` then opens a window with `js_api=Api()`.
- The frontend calls `window.pywebview.api.<method>(...)`, which returns a promise.
- Every `Api` method returns a uniform envelope `{ok, data}` / `{ok, error}`; `app.js`
  unwraps it and shows errors as a toast. This keeps error handling in one place.
- SQLite enforces the data rules: `UNIQUE(section_id, plot_number)`, a `CHECK`
  on status, and `ON DELETE CASCADE` from sections → graves → burials → documents.
- Uploaded files live in `documents/` **beside the database**, so pointing
  `GRAVEYARD_DB` elsewhere moves the attachments with it. The native file picker
  runs in Python, so file bytes never cross the JS bridge. Cascades delete the
  document *rows*; `api.py` collects the affected filenames before each delete and
  removes the files afterwards.

### Data model

| Table      | Purpose                                   | Key columns |
|------------|-------------------------------------------|-------------|
| `sections` | Cemetery sections                         | `code` (unique), `name` |
| `owners`   | Grave owners                              | `name` (unique), `contact` |
| `graves`   | Individual plots                          | `section_id`, `plot_number` (unique per section), `status`, `owner_id` (nullable, `LEFT JOIN owners`), `grave_ref` (shown as "Grave id"), `deed_id`, `date_purchased` |
| `burials`  | Burial records (a grave may have several) | `grave_id`, `deceased_name`, `date_of_death`, `date_of_burial` |
| `documents`| Uploaded files, owned by exactly one record | `section_id` / `grave_id` / `burial_id` (exactly one set, enforced by `CHECK`), `original_name`, `stored_name` |

---

## Setup & run

Requires **Python 3.10+**. On Windows the WebView2 runtime (bundled with modern
Windows 10/11) is used automatically.

```powershell
# 1. From the project root, create and activate a virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. (Optional) load example data so the app is usable on first run
python -m graveyard.seed             # add --reset to wipe existing data first

# 4. Launch the app
python run.py
```

The SQLite database is created at `data/graveyard.db` on first launch.

### Configuration

| Env var        | Default               | Purpose                          |
|----------------|-----------------------|----------------------------------|
| `GRAVEYARD_DB` | `data/graveyard.db`   | Override the database file path. |

```powershell
$env:GRAVEYARD_DB = "C:\path\to\custom.db"; python run.py
```

---

## Database migrations & seeding

- **Schema** lives in [graveyard/schema.sql](graveyard/schema.sql) and is applied
  idempotently (`CREATE TABLE IF NOT EXISTS`) on every startup via `init_db()`.
  For a fresh schema, stop the app and delete `data/graveyard.db`.
- **Columns added after release** cannot come from `CREATE TABLE IF NOT EXISTS`,
  so `init_db()` also applies the `MIGRATIONS` table in
  [graveyard/database.py](graveyard/database.py): any column listed there and
  missing from an existing database is added with `ALTER TABLE`. This is
  idempotent and preserves existing rows — adding a future column means adding
  one line to that dict.
- **Owner migration**: `init_db()` also runs `_migrate_owners`, which folds any
  existing `graves.owner_name` / `owner_contact` text into first-class `owners`
  rows (deduplicating by trimmed name, first contact wins by lowest
  `graves.id`) before dropping those two columns from `graves`. This step is
  **one-way** — the dropped columns cannot be recovered from the database
  afterwards — and self-heals if interrupted: it checks what's already been
  migrated on each `init_db()` call, so re-running it on a database it's
  already touched is a no-op.
- **Seed** with `python -m graveyard.seed` (idempotent inserts) or
  `python -m graveyard.seed --reset` to clear all tables first.

---

## Tests

```powershell
python tests/test_documents.py    # plain asserts, no test framework needed
python tests/test_graves.py
python tests/test_owners.py
```

`test_documents.py` covers the document store: attach/list/remove, cascade
cleanup actually deleting files from disk, the one-owner `CHECK`, and rejection
of oversized or unsupported files.

`test_graves.py` covers the grave reference fields and — importantly — the
migration: it builds a database with the pre-release `graves` shape, runs
`init_db()`, and asserts the new columns appear with existing rows intact.

`test_owners.py` covers owner CRUD, grave endpoints filtering/writing by
`owner_id`, and the `_migrate_owners` step itself: deduplication by trimmed
name, the first-contact-wins tiebreak, and that `owner_name` / `owner_contact`
are gone from `graves` afterwards.

## Packaging / deploy

For a standalone executable, build with PyInstaller and include the `web/` assets:

```powershell
pip install pyinstaller
pyinstaller --noconfirm --windowed --name "GraveInventory" `
  --add-data "graveyard/web;graveyard/web" `
  --add-data "graveyard/schema.sql;graveyard" `
  run.py
```

The result lands in `dist/GraveInventory/`. On macOS/Linux use `:` instead of `;`
in the `--add-data` separators. Ship the folder; the database is created next to
it on first run (or point `GRAVEYARD_DB` at a fixed location).
