"""Application entry point: builds the SQLite schema and opens the webview."""

from __future__ import annotations

from pathlib import Path

import webview

from .api import Api
from .database import init_db

WEB_DIR = Path(__file__).resolve().parent / "web"


def run() -> None:
    init_db()
    window = webview.create_window(
        title="Grave Inventory",
        url=str(WEB_DIR / "index.html"),
        js_api=Api(),
        width=1280,
        height=820,
        min_size=(960, 640),
    )
    # debug=True enables the right-click inspector during development.
    webview.start(debug=False)
    _ = window  # keep a reference so the window is not garbage collected


if __name__ == "__main__":
    run()
