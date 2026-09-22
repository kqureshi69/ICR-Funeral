"""The document store: bytes on disk, beside the database.

The ``documents`` table keeps the metadata; this module owns the files. Files
live next to the active database so that pointing ``GRAVEYARD_DB`` somewhere
else moves the attachments with it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

from . import database

MAX_BYTES = 25 * 1024 * 1024

ALLOWED_SUFFIXES = {
    ".pdf", ".jpg", ".jpeg", ".png", ".tif", ".tiff", ".doc", ".docx", ".txt",
}

# Filters offered by the native picker.
FILE_TYPES = (
    "Documents (*.pdf;*.doc;*.docx;*.txt)",
    "Images (*.jpg;*.jpeg;*.png;*.tif;*.tiff)",
    "All files (*.*)",
)


def docs_dir() -> Path:
    """Directory holding stored files, alongside the active database."""
    return database.DB_PATH.parent / "documents"


def path_for(stored_name: str) -> Path:
    return docs_dir() / stored_name


def store(src: str) -> dict:
    """Copy ``src`` into the store and return its metadata.

    The original filename is recorded for display only; the file on disk is
    named from a UUID so that user-supplied text never reaches the filesystem.
    """
    source = Path(src)
    if not source.is_file():
        raise ValueError(f"File not found: {source.name}")

    suffix = source.suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise ValueError(
            f"{source.name}: files of type {suffix or '(none)'} are not accepted."
        )

    size = source.stat().st_size
    if size > MAX_BYTES:
        raise ValueError(
            f"{source.name} is too large ({size / 1048576:.1f} MB); "
            f"the limit is {MAX_BYTES // 1048576} MB."
        )

    stored_name = f"{uuid.uuid4().hex}{suffix}"
    target = docs_dir()
    target.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target / stored_name)
    return {"original_name": source.name, "stored_name": stored_name, "size_bytes": size}


def discard(stored_names) -> None:
    """Delete stored files, ignoring any already gone."""
    for name in stored_names:
        try:
            path_for(name).unlink(missing_ok=True)
        except OSError:
            pass  # a file held open elsewhere should not fail the record delete


def open_externally(stored_name: str) -> None:
    """Hand the file to the operating system's default application."""
    path = path_for(stored_name)
    if not path.exists():
        raise ValueError("That file is missing from the document store.")
    if sys.platform == "win32":
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=True)
    else:
        subprocess.run(["xdg-open", str(path)], check=True)
