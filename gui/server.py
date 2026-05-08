"""Flask + rumps GUI for mp-pdf-bot. Run via launchd; serves http://localhost:<GUI_PORT>/."""
from __future__ import annotations
import os
import re
import shlex
import subprocess
import sys
import threading
from pathlib import Path

# Make repo root importable when run directly (python3 gui/server.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from flask import Flask, jsonify, send_file, send_from_directory, abort

from gui import status as gui_status
from gui.sync_state import SyncState

REPO_ROOT = Path(__file__).resolve().parent.parent
WEB_DIR = REPO_ROOT / "gui" / "web"
LAUNCHD_LABEL_WEWE = "com.mp-pdf-bot.wewe-rss"


def _load_config() -> dict:
    """Parse config.env (mirror of mybot.load_config)."""
    out = {}
    cfg = REPO_ROOT / "config.env"
    if not cfg.is_file():
        return out
    for raw in cfg.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        parts = shlex.split(value, posix=True)
        out[key.strip()] = parts[0] if parts else ""
    return out


CFG = _load_config()
GUI_PORT = int(CFG.get("GUI_PORT", "4001"))
WEWE_PORT = int(CFG.get("WEWE_RSS_PORT", "4000"))
DATA_DIR = REPO_ROOT / CFG.get("DATA_DIR", "./data").lstrip("./")
PDFS_DIR = REPO_ROOT / CFG.get("PDF_OUTPUT_DIR", "./pdfs").lstrip("./")
DB_PATH = DATA_DIR / "wewe-rss.db"

sync_state = SyncState()
app = Flask(__name__, static_folder=str(WEB_DIR), static_url_path="")


@app.route("/")
def index():
    return send_from_directory(str(WEB_DIR), "index.html")


@app.route("/api/status")
def api_status():
    return jsonify({
        "launchd": gui_status.launchd_state(LAUNCHD_LABEL_WEWE),
        "http": gui_status.http_health(WEWE_PORT),
        "db_kb": gui_status.db_size_kb(DB_PATH),
        "pdf_count": gui_status.pdf_count(PDFS_DIR),
        "syncing": sync_state.snapshot()["state"] == "running",
    })


def _run_flask():
    app.run(host="127.0.0.1", port=GUI_PORT, threaded=True, use_reloader=False)


if __name__ == "__main__":
    # No menu bar yet (Task 9) — just run Flask in foreground for now
    _run_flask()
