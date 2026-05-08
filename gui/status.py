"""Pure status helpers for the GUI — no Flask, no rumps imports."""
from __future__ import annotations
import os
import subprocess
from pathlib import Path


def db_size_kb(db_path: Path) -> int:
    """Return DB file size in KB, or 0 if missing."""
    try:
        return db_path.stat().st_size // 1024
    except FileNotFoundError:
        return 0


def pdf_count(pdfs_dir: Path) -> int:
    """Count PDF files recursively under pdfs_dir, 0 if dir missing."""
    if not pdfs_dir.is_dir():
        return 0
    return sum(1 for _ in pdfs_dir.rglob("*.pdf"))


def launchd_state(label: str) -> str:
    """Return 'running' if the launchd service is loaded, else 'stopped'."""
    r = subprocess.run(
        ["launchctl", "print", f"gui/{os.getuid()}/{label}"],
        capture_output=True, text=True,
    )
    return "running" if r.returncode == 0 else "stopped"


def http_health(port: int, timeout: float = 2.0) -> int:
    """Return HTTP status code from GET http://localhost:<port>/, or 0 on failure."""
    try:
        r = subprocess.run(
            ["curl", "--noproxy", "*", "-s", "-o", "/dev/null",
             "-w", "%{http_code}", "--max-time", str(timeout),
             f"http://localhost:{port}"],
            capture_output=True, text=True, timeout=timeout + 1,
        )
        return int(r.stdout.strip() or 0)
    except (subprocess.TimeoutExpired, ValueError):
        return 0


def overall_color(snapshot: dict) -> str:
    """Map a status snapshot to icon color: blue (syncing), green (healthy), red (otherwise)."""
    if snapshot.get("syncing"):
        return "blue"
    if snapshot.get("launchd") == "running" and snapshot.get("http") == 200:
        return "green"
    return "red"
