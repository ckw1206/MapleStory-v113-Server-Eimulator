import threading
import time

from botmcp.state import StateStore


def test_snapshot_roundtrip():
    s = StateStore()
    assert s.snapshot() is None
    s.update_snapshot({"hp": 5})
    assert s.snapshot() == {"hp": 5}

def test_chat_history_window():
    s = StateStore()
    for i in range(25):
        s.add_chat("p", f"m{i}")
    hist = s.chat_history()
    assert len(hist) == 20
    assert hist[-1]["message"] == "m24"
    assert set(hist[0]) == {"ts", "sender", "message"}

def test_drain_events_clears():
    s = StateStore()
    s.add_event("mob_killed", {"oid": 1})
    assert s.drain_events() == [{"event": "mob_killed", "data": {"oid": 1}}]
    assert s.drain_events() == []

def test_wait_times_out():
    s = StateStore()
    t0 = time.monotonic()
    assert s.wait_for_event(0.1) == "timeout"
    assert time.monotonic() - t0 < 1.0

def test_notable_event_wakes_waiter():
    s = StateStore()
    result = {}
    def waiter():
        result["reason"] = s.wait_for_event(5.0)
    t = threading.Thread(target=waiter)
    t.start()
    time.sleep(0.1)
    s.add_event("chat", {"text": "hi"})
    t.join(timeout=2.0)
    assert result["reason"] == "chat"

def test_non_notable_event_does_not_wake():
    s = StateStore()
    result = {}
    def waiter():
        result["reason"] = s.wait_for_event(0.3)
    t = threading.Thread(target=waiter)
    t.start()
    time.sleep(0.05)
    s.add_event("level_up", {})
    t.join(timeout=2.0)
    assert result["reason"] == "timeout"