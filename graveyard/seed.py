"""Populate the database with example sections, graves and burials.

Run with: ``python -m graveyard.seed``  (use --reset to wipe first).
"""

from __future__ import annotations

import sys

from . import documents
from .database import get_connection, init_db

SECTIONS = [
    ("A", "Garden of Peace", "Original section, established 1962."),
    ("B", "Memorial Lawn", "Flat-marker lawn section."),
    ("C", "Veterans Field", "Reserved for service members and spouses."),
]

# (name, contact)
OWNERS = [
    ("Estate of John Whitfield", "—"),
    ("Estate of John Whitfield - 2", "—"),
    ("Margaret Whitfield", "555-0142"),
    ("Acosta Family", "acosta.fam@example.com"),
    ("Daniel Okoro", "555-0199"),
    ("Sgt. Harold Bain (ret.)", "next-of-kin: 555-0177"),
]

# (section_code, plot_number, status, owner_name, notes)
GRAVES = [
    ("A", "1", "occupied", "Estate of John Whitfield", "Family plot, 4 spaces."),
    ("A", "2", "occupied", "Estate of John Whitfield - 2", ""),
    ("A", "3", "reserved", "Margaret Whitfield", "Pre-purchased 2019."),
    ("A", "4", "available", None, ""),
    ("B", "10", "occupied", "Acosta Family", ""),
    ("B", "11", "available", None, ""),
    ("B", "12", "reserved", "Daniel Okoro", ""),
    ("C", "V-1", "occupied", "Sgt. Harold Bain (ret.)", "Flag holder installed."),
    ("C", "V-2", "available", None, ""),
]

# (section_code, plot_number, deceased_name, date_of_death, date_of_burial, notes)
BURIALS = [
    ("A", "1", "John Whitfield", "1998-03-11", "1998-03-18", "Granite headstone."),
    ("A", "2", "Eleanor Whitfield", "2005-07-02", "2005-07-09", ""),
    ("B", "10", "Rosa Acosta", "2021-11-20", "2021-11-27", ""),
    ("C", "V-1", "Harold Bain", "2017-05-30", "2017-06-06", "Military honors."),
]


def seed(reset: bool = False) -> None:
    init_db()
    with get_connection() as conn:
        if reset:
            # Take the stored files too, or --reset leaves them orphaned.
            stored = [r["stored_name"] for r in conn.execute(
                "SELECT stored_name FROM documents")]
            conn.executescript(
                "DELETE FROM documents; DELETE FROM burials; "
                "DELETE FROM graves; DELETE FROM owners; DELETE FROM sections;"
            )
            documents.discard(stored)

        section_ids: dict[str, int] = {}
        for code, name, desc in SECTIONS:
            cur = conn.execute(
                "INSERT OR IGNORE INTO sections (code, name, description) VALUES (?, ?, ?)",
                (code, name, desc),
            )
            section_ids[code] = cur.lastrowid or conn.execute(
                "SELECT id FROM sections WHERE code = ?", (code,)
            ).fetchone()["id"]

        owner_ids: dict[str, int] = {}
        for name, contact in OWNERS:
            cur = conn.execute(
                "INSERT OR IGNORE INTO owners (name, contact) VALUES (?, ?)",
                (name, contact),
            )
            owner_ids[name] = cur.lastrowid or conn.execute(
                "SELECT id FROM owners WHERE name = ?", (name,)
            ).fetchone()["id"]

        grave_ids: dict[tuple[str, str], int] = {}
        for code, plot, status, owner, notes in GRAVES:
            owner_id = owner_ids[owner] if owner else None
            cur = conn.execute(
                """INSERT OR IGNORE INTO graves
                   (section_id, plot_number, status, owner_id, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (section_ids[code], plot, status, owner_id, notes),
            )
            grave_ids[(code, plot)] = cur.lastrowid or conn.execute(
                "SELECT id FROM graves WHERE section_id = ? AND plot_number = ?",
                (section_ids[code], plot),
            ).fetchone()["id"]

        for code, plot, name, dod, dob, notes in BURIALS:
            conn.execute(
                """INSERT INTO burials
                   (grave_id, deceased_name, date_of_death, date_of_burial, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (grave_ids[(code, plot)], name, dod, dob, notes),
            )

    print("Seed data inserted.")


if __name__ == "__main__":
    seed(reset="--reset" in sys.argv)
