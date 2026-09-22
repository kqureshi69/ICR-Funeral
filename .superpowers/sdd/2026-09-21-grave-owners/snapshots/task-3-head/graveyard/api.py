"""JS-facing API exposed to the webview via ``js_api``.

Every public method returns a JSON-serialisable envelope:
    {"ok": True,  "data": ...}      on success
    {"ok": False, "error": "..."}   on failure

The frontend awaits ``window.pywebview.api.<method>(...)`` and inspects ``ok``.
"""

from __future__ import annotations

import functools
import sqlite3
from typing import Any, Callable

import webview

from . import documents
from .database import get_connection


def _endpoint(func: Callable) -> Callable:
    """Wrap a method so exceptions become a uniform error envelope."""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        try:
            return {"ok": True, "data": func(self, *args, **kwargs)}
        except sqlite3.IntegrityError as exc:
            return {"ok": False, "error": _friendly_integrity_error(str(exc))}
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        except Exception as exc:  # pragma: no cover - defensive catch-all
            return {"ok": False, "error": f"Unexpected error: {exc}"}

    return wrapper


def _friendly_integrity_error(message: str) -> str:
    if "graves.section_id, graves.plot_number" in message:
        return "That plot number already exists in this section."
    if "sections.code" in message:
        return "A section with that code already exists."
    if "FOREIGN KEY constraint failed" in message:
        return "The selected section no longer exists. Reopen the form and choose a section."
    if "owners.name" in message:
        return "An owner with that name already exists."
    return message


def _rows(cursor) -> list[dict[str, Any]]:
    return [dict(row) for row in cursor.fetchall()]


def _require_section(conn, section_id) -> None:
    """Raise a clear error if section_id is missing or unknown."""
    if not section_id:
        raise ValueError("A section is required.")
    if conn.execute("SELECT 1 FROM sections WHERE id = ?", (section_id,)).fetchone() is None:
        raise ValueError("The selected section no longer exists. Reopen the form and choose a section.")


# A document hangs off exactly one of these; the table's CHECK enforces it.
OWNER_COLUMNS = {"section": "section_id", "grave": "grave_id", "burial": "burial_id"}
OWNER_TABLES = {"section": "sections", "grave": "graves", "burial": "burials"}

# Every document belonging to a record *or anything cascading from it*, so the
# files can be removed alongside the rows SQLite deletes for us.
_DESCENDANT_DOCS = {
    "burial": ("SELECT stored_name FROM documents WHERE burial_id = ?", 1),
    "grave": ("""SELECT stored_name FROM documents
                 WHERE grave_id = ?
                    OR burial_id IN (SELECT id FROM burials WHERE grave_id = ?)""", 2),
    "section": ("""SELECT stored_name FROM documents
                   WHERE section_id = ?
                      OR grave_id IN (SELECT id FROM graves WHERE section_id = ?)
                      OR burial_id IN (SELECT id FROM burials WHERE grave_id IN
                             (SELECT id FROM graves WHERE section_id = ?))""", 3),
}


def _owner_column(owner_type: str) -> str:
    if owner_type not in OWNER_COLUMNS:
        raise ValueError(f"Unknown document owner: {owner_type}")
    return OWNER_COLUMNS[owner_type]


def _require_owner(conn, owner_type, owner_id) -> str:
    """Raise unless the owning record exists; return its document column."""
    column = _owner_column(owner_type)
    row = conn.execute(
        f"SELECT 1 FROM {OWNER_TABLES[owner_type]} WHERE id = ?", (owner_id,)
    ).fetchone()
    if not owner_id or row is None:
        raise ValueError("That record no longer exists. Reopen it and try again.")
    return column


def _descendant_docs(conn, owner_type, owner_id) -> list[str]:
    _owner_column(owner_type)  # rejects an unknown owner type
    sql, repeats = _DESCENDANT_DOCS[owner_type]
    return [r["stored_name"] for r in conn.execute(sql, (owner_id,) * repeats)]


class Api:
    """All methods here are reachable from JavaScript."""

    # ----- Sections -------------------------------------------------------
    @_endpoint
    def list_sections(self) -> list[dict]:
        with get_connection() as conn:
            return _rows(
                conn.execute(
                    """
                    SELECT s.*,
                           COUNT(g.id)                                       AS total_plots,
                           SUM(g.status = 'available') AS available_plots,
                           SUM(g.status = 'occupied')  AS occupied_plots,
                           (SELECT COUNT(*) FROM documents d
                             WHERE d.section_id = s.id)               AS doc_count
                    FROM sections s
                    LEFT JOIN graves g ON g.section_id = s.id
                    GROUP BY s.id
                    ORDER BY s.code
                    """
                )
            )

    @_endpoint
    def create_section(self, code: str, name: str, description: str = "") -> int:
        code, name = code.strip(), name.strip()
        if not code or not name:
            raise ValueError("Section code and name are required.")
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO sections (code, name, description) VALUES (?, ?, ?)",
                (code, name, description.strip()),
            )
            return cur.lastrowid

    @_endpoint
    def update_section(self, section_id: int, code: str, name: str, description: str = "") -> bool:
        code, name = code.strip(), name.strip()
        if not code or not name:
            raise ValueError("Section code and name are required.")
        with get_connection() as conn:
            conn.execute(
                "UPDATE sections SET code = ?, name = ?, description = ? WHERE id = ?",
                (code, name, description.strip(), section_id),
            )
        return True

    @_endpoint
    def delete_section(self, section_id: int) -> bool:
        with get_connection() as conn:
            # Collected before the delete: afterwards the rows are gone and the
            # files would have nothing pointing at them.
            doomed = _descendant_docs(conn, "section", section_id)
            conn.execute("DELETE FROM sections WHERE id = ?", (section_id,))
        documents.discard(doomed)
        return True

    # ----- Owners ---------------------------------------------------------
    @_endpoint
    def list_owners(self, search: str = "") -> list[dict]:
        clauses, params = [], []
        if search.strip():
            term = f"%{search.strip()}%"
            clauses.append("(o.name LIKE ? OR o.contact LIKE ?)")
            params.extend([term, term])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with get_connection() as conn:
            return _rows(conn.execute(
                f"""SELECT o.*, (SELECT COUNT(*) FROM graves g WHERE g.owner_id = o.id)
                           AS grave_count
                    FROM owners o {where} ORDER BY o.name""", params))

    @_endpoint
    def get_owner(self, owner_id: int) -> dict:
        with get_connection() as conn:
            owner = conn.execute("SELECT * FROM owners WHERE id = ?", (owner_id,)).fetchone()
            if owner is None:
                raise ValueError("Owner not found.")
            graves = _rows(conn.execute(
                """SELECT g.id, g.plot_number, g.status, s.code AS section_code
                   FROM graves g JOIN sections s ON s.id = g.section_id
                   WHERE g.owner_id = ? ORDER BY s.code, g.plot_number""", (owner_id,)))
        result = dict(owner)
        result["graves"] = graves
        return result

    @_endpoint
    def create_owner(self, name: str, contact: str = "", address: str = "",
                     notes: str = "") -> int:
        name = name.strip()
        if not name:
            raise ValueError("Owner name is required.")
        with get_connection() as conn:
            cur = conn.execute(
                "INSERT INTO owners (name, contact, address, notes) VALUES (?, ?, ?, ?)",
                (name, contact.strip(), address.strip(), notes.strip()))
            return cur.lastrowid

    @_endpoint
    def update_owner(self, owner_id: int, name: str, contact: str = "",
                     address: str = "", notes: str = "") -> bool:
        name = name.strip()
        if not name:
            raise ValueError("Owner name is required.")
        with get_connection() as conn:
            conn.execute(
                """UPDATE owners SET name = ?, contact = ?, address = ?, notes = ?,
                   updated_at = datetime('now') WHERE id = ?""",
                (name, contact.strip(), address.strip(), notes.strip(), owner_id))
        return True

    @_endpoint
    def delete_owner(self, owner_id: int) -> bool:
        with get_connection() as conn:
            owner = conn.execute(
                "SELECT name FROM owners WHERE id = ?", (owner_id,)).fetchone()
            if owner is None:
                raise ValueError("Owner not found.")
            held = conn.execute(
                "SELECT COUNT(*) c FROM graves WHERE owner_id = ?", (owner_id,)
            ).fetchone()["c"]
            if held:
                raise ValueError(
                    f"{owner['name']} still holds {held} "
                    f"plot{'' if held == 1 else 's'}. Reassign them first.")
            conn.execute("DELETE FROM owners WHERE id = ?", (owner_id,))
        return True

    # ----- Graves ---------------------------------------------------------
    @_endpoint
    def list_graves(self, section_id=None, status=None, search="") -> list[dict]:
        clauses, params = [], []
        if section_id:
            clauses.append("g.section_id = ?")
            params.append(section_id)
        if status:
            clauses.append("g.status = ?")
            params.append(status)
        if search.strip():
            term = f"%{search.strip()}%"
            clauses.append("(g.plot_number LIKE ? OR g.owner_name LIKE ?"
                           " OR g.grave_ref LIKE ? OR g.deed_id LIKE ?)")
            params.extend([term, term, term, term])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        with get_connection() as conn:
            return _rows(
                conn.execute(
                    f"""
                    SELECT g.*, s.code AS section_code, s.name AS section_name,
                           (SELECT COUNT(*) FROM documents d
                             WHERE d.grave_id = g.id) AS doc_count
                    FROM graves g
                    JOIN sections s ON s.id = g.section_id
                    {where}
                    ORDER BY s.code, g.plot_number
                    """,
                    params,
                )
            )

    @_endpoint
    def get_grave(self, grave_id: int) -> dict:
        with get_connection() as conn:
            grave = conn.execute(
                """
                SELECT g.*, s.code AS section_code, s.name AS section_name,
                       (SELECT COUNT(*) FROM documents d
                         WHERE d.grave_id = g.id) AS doc_count
                FROM graves g JOIN sections s ON s.id = g.section_id
                WHERE g.id = ?
                """,
                (grave_id,),
            ).fetchone()
            if grave is None:
                raise ValueError("Grave not found.")
            burials = _rows(
                conn.execute(
                    """SELECT b.*, (SELECT COUNT(*) FROM documents d
                                     WHERE d.burial_id = b.id) AS doc_count
                       FROM burials b WHERE b.grave_id = ?
                       ORDER BY b.date_of_burial DESC, b.id DESC""",
                    (grave_id,),
                )
            )
        result = dict(grave)
        result["burials"] = burials
        return result

    @_endpoint
    def create_grave(self, section_id, plot_number, status="available",
                     owner_name="", owner_contact="", notes="",
                     grave_ref="", deed_id="", date_purchased="") -> int:
        if not str(plot_number).strip():
            raise ValueError("Plot number is required.")
        with get_connection() as conn:
            _require_section(conn, section_id)
            cur = conn.execute(
                """INSERT INTO graves
                   (section_id, plot_number, status, owner_name, owner_contact,
                    notes, grave_ref, deed_id, date_purchased)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (section_id, str(plot_number).strip(), status,
                 owner_name.strip(), owner_contact.strip(), notes.strip(),
                 grave_ref.strip(), deed_id.strip(), date_purchased.strip()),
            )
            return cur.lastrowid

    @_endpoint
    def update_grave(self, grave_id, section_id, plot_number, status,
                     owner_name="", owner_contact="", notes="",
                     grave_ref="", deed_id="", date_purchased="") -> bool:
        if not str(plot_number).strip():
            raise ValueError("Plot number is required.")
        with get_connection() as conn:
            _require_section(conn, section_id)
            conn.execute(
                """UPDATE graves
                   SET section_id = ?, plot_number = ?, status = ?,
                       owner_name = ?, owner_contact = ?, notes = ?,
                       grave_ref = ?, deed_id = ?, date_purchased = ?,
                       updated_at = datetime('now')
                   WHERE id = ?""",
                (section_id, str(plot_number).strip(), status,
                 owner_name.strip(), owner_contact.strip(), notes.strip(),
                 grave_ref.strip(), deed_id.strip(), date_purchased.strip(), grave_id),
            )
        return True

    @_endpoint
    def set_status(self, grave_id: int, status: str) -> bool:
        if status not in ("available", "reserved", "occupied"):
            raise ValueError("Invalid status.")
        with get_connection() as conn:
            conn.execute(
                "UPDATE graves SET status = ?, updated_at = datetime('now') WHERE id = ?",
                (status, grave_id),
            )
        return True

    @_endpoint
    def delete_grave(self, grave_id: int) -> bool:
        with get_connection() as conn:
            doomed = _descendant_docs(conn, "grave", grave_id)
            conn.execute("DELETE FROM graves WHERE id = ?", (grave_id,))
        documents.discard(doomed)
        return True

    # ----- Burials --------------------------------------------------------
    @_endpoint
    def add_burial(self, grave_id, deceased_name, date_of_death="",
                   date_of_burial="", notes="") -> int:
        if not deceased_name.strip():
            raise ValueError("Deceased name is required.")
        with get_connection() as conn:
            cur = conn.execute(
                """INSERT INTO burials
                   (grave_id, deceased_name, date_of_death, date_of_burial, notes)
                   VALUES (?, ?, ?, ?, ?)""",
                (grave_id, deceased_name.strip(), date_of_death.strip(),
                 date_of_burial.strip(), notes.strip()),
            )
            # Recording a burial marks the grave as occupied.
            conn.execute(
                "UPDATE graves SET status = 'occupied', updated_at = datetime('now') WHERE id = ?",
                (grave_id,),
            )
            return cur.lastrowid

    @_endpoint
    def delete_burial(self, burial_id: int) -> bool:
        with get_connection() as conn:
            doomed = _descendant_docs(conn, "burial", burial_id)
            conn.execute("DELETE FROM burials WHERE id = ?", (burial_id,))
        documents.discard(doomed)
        return True

    # ----- Documents ------------------------------------------------------
    @_endpoint
    def list_documents(self, owner_type: str, owner_id: int) -> list[dict]:
        column = _owner_column(owner_type)
        with get_connection() as conn:
            return _rows(
                conn.execute(
                    f"""SELECT * FROM documents WHERE {column} = ?
                        ORDER BY created_at DESC, id DESC""",
                    (owner_id,),
                )
            )

    def _attach(self, owner_type, owner_id, paths) -> list[dict]:
        """Copy files into the store and record them. All-or-nothing.

        Not an endpoint: shared by ``attach_files`` (used by tests) and
        ``add_documents`` (which sources its paths from the native picker).
        """
        if not paths:
            return []
        copied, added = [], []
        try:
            with get_connection() as conn:
                column = _require_owner(conn, owner_type, owner_id)
                for src in paths:
                    meta = documents.store(src)
                    copied.append(meta["stored_name"])
                    cur = conn.execute(
                        f"""INSERT INTO documents
                            ({column}, original_name, stored_name, size_bytes)
                            VALUES (?, ?, ?, ?)""",
                        (owner_id, meta["original_name"],
                         meta["stored_name"], meta["size_bytes"]),
                    )
                    added.append({**meta, "id": cur.lastrowid})
        except Exception:
            # The transaction rolled back, so the copied files are unreferenced.
            documents.discard(copied)
            raise
        return added

    @_endpoint
    def attach_files(self, owner_type: str, owner_id: int, paths: list) -> list[dict]:
        return self._attach(owner_type, owner_id, list(paths))

    @_endpoint
    def add_documents(self, owner_type: str, owner_id: int) -> list[dict]:
        """Open the native file picker, then store whatever was chosen."""
        _owner_column(owner_type)
        window = webview.active_window()
        if window is None:  # pragma: no cover - requires a running window
            raise ValueError("No application window is available.")
        chosen = window.create_file_dialog(
            webview.OPEN_DIALOG, allow_multiple=True, file_types=documents.FILE_TYPES
        )
        if not chosen:
            return []  # the user cancelled
        return self._attach(owner_type, owner_id, list(chosen))

    @_endpoint
    def open_document(self, doc_id: int) -> bool:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT stored_name FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
        if row is None:
            raise ValueError("Document not found.")
        documents.open_externally(row["stored_name"])
        return True

    @_endpoint
    def delete_document(self, doc_id: int) -> bool:
        with get_connection() as conn:
            row = conn.execute(
                "SELECT stored_name FROM documents WHERE id = ?", (doc_id,)
            ).fetchone()
            if row is None:
                raise ValueError("Document not found.")
            conn.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
        documents.discard([row["stored_name"]])
        return True

    @_endpoint
    def describe_delete(self, owner_type: str, owner_id: int) -> dict:
        """What a delete would take with it, so paperwork is never lost silently."""
        _owner_column(owner_type)
        counts = {"graves": 0, "burials": 0, "documents": 0}
        with get_connection() as conn:
            if owner_type == "section":
                counts["graves"] = conn.execute(
                    "SELECT COUNT(*) c FROM graves WHERE section_id = ?", (owner_id,)
                ).fetchone()["c"]
                counts["burials"] = conn.execute(
                    """SELECT COUNT(*) c FROM burials WHERE grave_id IN
                       (SELECT id FROM graves WHERE section_id = ?)""", (owner_id,)
                ).fetchone()["c"]
            elif owner_type == "grave":
                counts["burials"] = conn.execute(
                    "SELECT COUNT(*) c FROM burials WHERE grave_id = ?", (owner_id,)
                ).fetchone()["c"]
            counts["documents"] = len(_descendant_docs(conn, owner_type, owner_id))
        return counts

    # ----- Dashboard ------------------------------------------------------
    @_endpoint
    def stats(self) -> dict:
        with get_connection() as conn:
            row = conn.execute(
                """SELECT
                       COUNT(*)                       AS total,
                       SUM(status = 'available')      AS available,
                       SUM(status = 'reserved')       AS reserved,
                       SUM(status = 'occupied')       AS occupied
                   FROM graves"""
            ).fetchone()
            sections = conn.execute("SELECT COUNT(*) AS c FROM sections").fetchone()["c"]
        data = {k: (v or 0) for k, v in dict(row).items()}
        data["sections"] = sections
        return data
