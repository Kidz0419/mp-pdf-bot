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


def _sync_worker():
    """Run ./mybot sync in subprocess; parse summary line; update sync_state."""
    log = REPO_ROOT / "logs" / "sync-gui.log"
    log.parent.mkdir(exist_ok=True)
    with log.open("a") as f:
        proc = subprocess.run(
            [str(REPO_ROOT / "mybot"), "sync"],
            cwd=REPO_ROOT, stdout=f, stderr=subprocess.STDOUT, text=True,
        )
    # Parse last "完成：成功 N / 跳过 M / 失败 K" from log to extract counts
    ok = fail = skip = 0
    if log.exists():
        for ln in reversed(log.read_text().splitlines()[-20:]):
            m = re.search(r"成功\s+(\d+)\s*/\s*跳过\s+(\d+)\s*/\s*失败\s+(\d+)", ln)
            if m:
                ok, skip, fail = int(m.group(1)), int(m.group(2)), int(m.group(3))
                break
    sync_state.finish({"ok": ok, "skip": skip, "fail": fail, "exit_code": proc.returncode})


@app.route("/api/sync", methods=["POST"])
def api_sync():
    result = sync_state.start()
    if result == "started":
        threading.Thread(target=_sync_worker, daemon=True).start()
    return jsonify({"state": result})


@app.route("/api/sync/status")
def api_sync_status():
    return jsonify(sync_state.snapshot())


@app.route("/api/feeds")
def api_feeds():
    """List public account dirs under PDFS_DIR with their PDF files."""
    out = []
    if PDFS_DIR.is_dir():
        for d in sorted(PDFS_DIR.iterdir()):
            if not d.is_dir():
                continue
            pdfs = sorted(
                [{"name": p.name, "size_kb": p.stat().st_size // 1024}
                 for p in d.glob("*.pdf")],
                key=lambda x: x["name"], reverse=True,
            )
            out.append({"mp_name": d.name, "count": len(pdfs), "pdfs": pdfs})
    return jsonify(out)


@app.route("/pdfs/<path:relpath>")
def serve_pdf(relpath):
    """Serve a PDF file inline. Path is constrained to PDFS_DIR."""
    target = (PDFS_DIR / relpath).resolve()
    # Prevent path traversal
    if not str(target).startswith(str(PDFS_DIR.resolve())):
        abort(403)
    if not target.is_file() or target.suffix != ".pdf":
        abort(404)
    return send_file(str(target), mimetype="application/pdf",
                     as_attachment=False, download_name=target.name)


def _run_flask():
    app.run(host="127.0.0.1", port=GUI_PORT, threaded=True, use_reloader=False)


if __name__ == "__main__":
    # No menu bar yet (Task 9) — just run Flask in foreground for now
    _run_flask()
