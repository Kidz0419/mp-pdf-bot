"""Tests for gui.status — pure helpers that read system state."""
import os
import sys
from pathlib import Path

# Make repo root importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gui import status


def test_db_size_kb_returns_kb_or_zero(tmp_path):
    db = tmp_path / "wewe-rss.db"
    assert status.db_size_kb(db) == 0   # missing
    db.write_bytes(b"x" * 2048)
    assert status.db_size_kb(db) == 2

def test_pdf_count_recursive(tmp_path):
    (tmp_path / "金渐成").mkdir()
    (tmp_path / "金渐成" / "a.pdf").write_text("")
    (tmp_path / "金渐成" / "b.pdf").write_text("")
    (tmp_path / "其他").mkdir()
    (tmp_path / "其他" / "c.pdf").write_text("")
    (tmp_path / "其他" / "not-a-pdf.txt").write_text("")
    assert status.pdf_count(tmp_path) == 3

def test_pdf_count_missing_dir_is_zero(tmp_path):
    assert status.pdf_count(tmp_path / "does-not-exist") == 0

def test_overall_color_running():
    assert status.overall_color({"launchd": "running", "http": 200, "syncing": False}) == "green"

def test_overall_color_syncing_overrides():
    assert status.overall_color({"launchd": "running", "http": 200, "syncing": True}) == "blue"

def test_overall_color_stopped():
    assert status.overall_color({"launchd": "stopped", "http": 0, "syncing": False}) == "red"

def test_overall_color_partial_is_red():
    # launchd running but HTTP not responding (still booting / crashed inside)
    assert status.overall_color({"launchd": "running", "http": 0, "syncing": False}) == "red"
