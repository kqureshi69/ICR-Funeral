-- Grave Inventory schema (SQLite)
PRAGMA foreign_keys = ON;

-- Cemetery sections (e.g. "A", "Garden of Peace").
CREATE TABLE IF NOT EXISTS sections (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    code        TEXT NOT NULL UNIQUE,
    name        TEXT NOT NULL,
    description TEXT,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Plot owners. A grave is filed under exactly one owner (or none).
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

-- Individual grave plots. A plot number is unique within its section.
CREATE TABLE IF NOT EXISTS graves (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id    INTEGER NOT NULL REFERENCES sections(id) ON DELETE CASCADE,
    plot_number   TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'available'
                  CHECK (status IN ('available', 'reserved', 'occupied')),
    owner_id      INTEGER REFERENCES owners(id),
    notes         TEXT,
    grave_ref      TEXT NOT NULL DEFAULT '',   -- shown as "Grave id"
    deed_id        TEXT NOT NULL DEFAULT '',
    date_purchased TEXT NOT NULL DEFAULT '',   -- ISO date
    created_at    TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE (section_id, plot_number)
);

-- Burial records. A grave may hold more than one burial over time.
CREATE TABLE IF NOT EXISTS burials (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    grave_id       INTEGER NOT NULL REFERENCES graves(id) ON DELETE CASCADE,
    deceased_name  TEXT NOT NULL,
    date_of_death  TEXT,
    date_of_burial TEXT,
    notes          TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_graves_section ON graves(section_id);
CREATE INDEX IF NOT EXISTS idx_graves_status  ON graves(status);
CREATE INDEX IF NOT EXISTS idx_burials_grave  ON burials(grave_id);

-- Uploaded documents (deeds, certificates, site plans). Exactly one owner
-- column is set, enforced by the CHECK below; ON DELETE CASCADE removes the
-- row with its owner, and the application removes the file from disk.
CREATE TABLE IF NOT EXISTS documents (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    section_id    INTEGER REFERENCES sections(id) ON DELETE CASCADE,
    grave_id      INTEGER REFERENCES graves(id)   ON DELETE CASCADE,
    burial_id     INTEGER REFERENCES burials(id)  ON DELETE CASCADE,
    original_name TEXT    NOT NULL,
    stored_name   TEXT    NOT NULL UNIQUE,
    size_bytes    INTEGER NOT NULL,
    created_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    CHECK ((section_id IS NOT NULL)
         + (grave_id   IS NOT NULL)
         + (burial_id  IS NOT NULL) = 1)
);

CREATE INDEX IF NOT EXISTS idx_documents_section ON documents(section_id);
CREATE INDEX IF NOT EXISTS idx_documents_grave   ON documents(grave_id);
CREATE INDEX IF NOT EXISTS idx_documents_burial  ON documents(burial_id);
