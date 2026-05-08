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


import rumps

# Map color → unicode character for the menu bar title (rumps doesn't easily
# do colored dot icons; emoji works on macOS menu bar).
_COLOR_DOT = {"green": "🟢", "red": "🔴", "blue": "🔵"}


class MpPdfBotApp(rumps.App):
    def __init__(self):
        super().__init__("🔵 mp-pdf-bot", quit_button=None)
        self.menu = [
            "Open Dashboard",
            "Sync Now",
            "Open Web UI",
            "Open PDFs Folder",
            None,
            "Stop wewe-rss",
            "Start wewe-rss",
            None,
            "Quit GUI",
        ]
        self._refresh_timer = rumps.Timer(self._refresh, 5)
        self._refresh_timer.start()

    def _refresh(self, _sender):
        snap = {
            "launchd": gui_status.launchd_state(LAUNCHD_LABEL_WEWE),
            "http": gui_status.http_health(WEWE_PORT),
            "syncing": sync_state.snapshot()["state"] == "running",
        }
        color = gui_status.overall_color(snap)
        self.title = f"{_COLOR_DOT[color]} mp-pdf-bot"

    @rumps.clicked("Open Dashboard")
    def open_dashboard(self, _):
        subprocess.run(["open", f"http://localhost:{WEWE_PORT}/dash"])

    @rumps.clicked("Sync Now")
    def sync_now(self, _):
        if sync_state.start() == "started":
            threading.Thread(target=_sync_worker, daemon=True).start()
            rumps.notification("mp-pdf-bot", "", "开始同步")

    @rumps.clicked("Open Web UI")
    def open_web_ui(self, _):
        subprocess.run(["open", f"http://localhost:{GUI_PORT}/"])

    @rumps.clicked("Open PDFs Folder")
    def open_pdfs(self, _):
        PDFS_DIR.mkdir(exist_ok=True)
        subprocess.run(["open", str(PDFS_DIR)])

    @rumps.clicked("Stop wewe-rss")
    def stop_wewe(self, _):
        subprocess.run(
            ["launchctl", "bootout", f"gui/{os.getuid()}/{LAUNCHD_LABEL_WEWE}"],
            capture_output=True,
        )

    @rumps.clicked("Start wewe-rss")
    def start_wewe(self, _):
        plist = Path.home() / "Library/LaunchAgents" / f"{LAUNCHD_LABEL_WEWE}.plist"
        if plist.exists():
            subprocess.run(
                ["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist)],
                capture_output=True,
            )

    @rumps.clicked("Quit GUI")
    def quit_gui(self, _):
        rumps.quit_application()


if __name__ == "__main__":
    threading.Thread(target=_run_flask, daemon=True).start()
    MpPdfBotApp().run()
