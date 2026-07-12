"""Thread-safe world-state cache shared between the WS thread and MCP tool calls."""

import threading
import time
from collections import deque

NOTABLE_EVENTS = {"chat", "damaged", "died", "mob_killed"}


class StateStore:
    def __init__(self):
        self._cond = threading.Condition()
        self._snapshot = None
        self._chat = deque(maxlen=20)
        self._events = deque(maxlen=64)
        self._wake_reason = None

    def update_snapshot(self, snap: dict):
        with self._cond:
            self._snapshot = snap

    def snapshot(self) -> dict | None:
        with self._cond:
            return self._snapshot

    def add_chat(self, sender: str, message: str):
        with self._cond:
            self._chat.append({"ts": time.strftime("%H:%M:%S"), "sender": sender, "message": message})

    def chat_history(self) -> list:
        with self._cond:
            return list(self._chat)

    def add_event(self, name: str, data: dict):
        with self._cond:
            self._events.append({"event": name, "data": data})
            if name in NOTABLE_EVENTS:
                self._wake_reason = name
                self._cond.notify_all()

    def drain_events(self) -> list:
        with self._cond:
            out = list(self._events)
            self._events.clear()
            return out

    def wait_for_event(self, timeout_s: float) -> str:
        deadline = time.monotonic() + timeout_s
        with self._cond:
            self._wake_reason = None
            while self._wake_reason is None:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return "timeout"
                self._cond.wait(remaining)
            return self._wake_reason