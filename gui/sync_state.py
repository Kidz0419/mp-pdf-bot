"""Thread-safe sync state machine: idle → running → idle (with last_result)."""
from __future__ import annotations
import threading
import time
from typing import Optional


class SyncState:
    def __init__(self):
        self._lock = threading.Lock()
        self._state = "idle"
        self._last_result: Optional[dict] = None

    def start(self) -> str:
        """Transition idle → running. Returns 'started' or 'running' if already going."""
        with self._lock:
            if self._state == "running":
                return "running"
            self._state = "running"
            return "started"

    def finish(self, result: dict) -> None:
        """Transition running → idle, record result. No-op if already idle."""
        with self._lock:
            if self._state != "running":
                return
            self._state = "idle"
            self._last_result = {**result, "finished_at": time.time()}

    def snapshot(self) -> dict:
        with self._lock:
            return {"state": self._state, "last_result": self._last_result}
