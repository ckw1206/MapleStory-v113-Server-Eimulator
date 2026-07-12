import json
import threading
import time

import pytest

from botmcp.state import StateStore
from botmcp.ws_client import BotClient

CFG = {
    "ws_url": "ws://127.0.0.1:9999/ws",
    "token": "t",
    "spawn_map_id": 100000000,
    "potion_item_id": 2000002,
    "hp_threshold": 0.40,
}


class FakeWS:
    """Captures frames; lets tests reply like the server would."""
    def __init__(self):
        self.sent = []
        self.sent_signal = threading.Event()

    def send(self, raw):
        self.sent.append(json.loads(raw))
        self.sent_signal.set()


@pytest.fixture
def client():
    store = StateStore()
    c = BotClient(CFG, store)
    c._ws = FakeWS()
    c._connected.set()   # pretend the socket is up
    return c


def _reply_done(client, seq):
    client._on_message(None, json.dumps({"type": "action_done", "seq": seq, "action": "x"}))


def test_send_action_correlates_reply(client):
    result = {}
    t = threading.Thread(target=lambda: result.update(client.send_action("idle")))
    t.start()
    assert client._ws.sent_signal.wait(2.0)
    sent = client._ws.sent[0]
    assert sent["action"] == "idle" and sent["seq"] >= 1
    _reply_done(client, sent["seq"])
    t.join(timeout=2.0)
    assert result["status"] == "success"

def test_send_action_failure_reason(client):
    result = {}
    t = threading.Thread(target=lambda: result.update(client.send_action("attack", {"mobId": 1})))
    t.start()
    assert client._ws.sent_signal.wait(2.0)
    seq = client._ws.sent[0]["seq"]
    client._on_message(None, json.dumps({"type": "action_failed", "seq": seq, "reason": "not_spawned"}))
    t.join(timeout=2.0)
    assert result == {"status": "failed", "reason": "not_spawned"}

def test_snapshot_updates_store(client):
    client._on_message(None, json.dumps({"type": "snapshot", "data": {"hp": 500, "maxHp": 500}}))
    assert client.store.snapshot() == {"hp": 500, "maxHp": 500}

def test_chat_event_fills_history_and_ring(client):
    client._on_message(None, json.dumps(
        {"type": "event", "data": {"event": "chat", "senderId": 2, "senderName": "kyle", "text": "hi"}}))
    assert client.store.chat_history()[0]["sender"] == "kyle"
    assert client.store.drain_events()[0]["event"] == "chat"

def test_reflex_fires_below_threshold(client):
    client._on_message(None, json.dumps({"type": "snapshot", "data": {"hp": 100, "maxHp": 500}}))
    assert client._ws.sent_signal.wait(2.0)
    assert client._ws.sent[0] == {
        "action": "use_item", "seq": client._ws.sent[0]["seq"],
        "args": {"itemId": 2000002},
    }

def test_reflex_respects_cooldown(client):
    for _ in range(3):
        client._on_message(None, json.dumps({"type": "snapshot", "data": {"hp": 100, "maxHp": 500}}))
    time.sleep(0.3)
    assert len([m for m in client._ws.sent if m["action"] == "use_item"]) == 1

def test_reflex_skips_above_threshold_and_when_dead(client):
    client._on_message(None, json.dumps({"type": "snapshot", "data": {"hp": 400, "maxHp": 500}}))
    client._on_message(None, json.dumps({"type": "snapshot", "data": {"hp": 0, "maxHp": 500}}))
    time.sleep(0.3)
    assert client._ws.sent == []

def test_reflex_backs_off_on_failure(client):
    client._on_message(None, json.dumps({"type": "snapshot", "data": {"hp": 100, "maxHp": 500}}))
    assert client._ws.sent_signal.wait(2.0)
    seq = client._ws.sent[0]["seq"]
    client._on_message(None, json.dumps({"type": "action_failed", "seq": seq, "reason": "no_player_on_map"}))
    for _ in range(10):
        if client._potion_failures == 1:
            break
        time.sleep(0.05)
    assert client._potion_failures == 1
    client._ws.sent.clear()
    client._ws.sent_signal.clear()
    client._on_message(None, json.dumps({"type": "snapshot", "data": {"hp": 100, "maxHp": 500}}))
    time.sleep(0.3)
    assert not any(m["action"] == "use_item" for m in client._ws.sent)