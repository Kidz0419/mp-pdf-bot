"""Tests for gui.sync_state — thread-safe sync execution state."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gui.sync_state import SyncState


def test_initial_state_is_idle():
    s = SyncState()
    snap = s.snapshot()
    assert snap["state"] == "idle"
    assert snap["last_result"] is None

def test_start_returns_started_when_idle():
    s = SyncState()
    assert s.start() == "started"
    assert s.snapshot()["state"] == "running"

def test_start_returns_running_when_already_running():
    s = SyncState()
    s.start()
    assert s.start() == "running"

def test_finish_records_result_and_returns_to_idle():
    s = SyncState()
    s.start()
    s.finish({"ok": 5, "fail": 1, "skip": 2})
    snap = s.snapshot()
    assert snap["state"] == "idle"
    assert snap["last_result"]["ok"] == 5
    assert snap["last_result"]["fail"] == 1
    assert snap["last_result"]["finished_at"] > 0

def test_finish_when_not_running_is_noop():
    s = SyncState()
    s.finish({"ok": 0})
    assert s.snapshot()["state"] == "idle"
    assert s.snapshot()["last_result"] is None
