"""WebSocket transport: auth, auto-spawn, reconnect, seq correlation, reflex layer."""

import json
import logging
import threading
import time

import websocket

log = logging.getLogger("botmcp.ws")

RECONNECT_DELAY_S = 3.0
RESPAWN_DELAY_S = 3.0
POTION_COOLDOWN_S = 2.0


class BotClient:
    def __init__(self, cfg: dict, store):
        self.cfg = cfg
        self.store = store
        self._seq = 0
        self._seq_lock = threading.Lock()
        self._pending = {}  # seq -> {"event": threading.Event(), "result": dict | None}
        self._ws = None
        self._connected = threading.Event()
        self._stop = False
        self._last_potion = 0.0

    # ---- public API ----

    def start(self):
        threading.Thread(target=self._run_loop, name="botmcp-ws", daemon=True).start()

    def send_action(self, action: str, args: dict | None = None, timeout: float = 10.0) -> dict:
        if not self._connected.wait(timeout):
            return {"status": "failed", "reason": "not_connected"}
        with self._seq_lock:
            self._seq += 1
            seq = self._seq
        waiter = {"event": threading.Event(), "result": None}
        self._pending[seq] = waiter
        msg = {"action": action, "seq": seq}
        if args is not None:
            msg["args"] = args
        try:
            self._ws.send(json.dumps(msg))
        except Exception as e:
            self._pending.pop(seq, None)
            return {"status": "failed", "reason": f"send_error: {e}"}
        if not waiter["event"].wait(timeout):
            self._pending.pop(seq, None)
            return {"status": "failed", "reason": "reply_timeout"}
        return waiter["result"]

    # ---- connection loop ----

    def _run_loop(self):
        url = f"{self.cfg['ws_url']}?token={self.cfg['token']}"
        while not self._stop:
            ws = websocket.WebSocketApp(
                url,
                on_open=self._on_open,
                on_message=self._on_message,
                on_close=self._on_close,
                on_error=lambda _ws, e: log.warning("ws error: %s", e),
            )
            self._ws = ws
            ws.run_forever(ping_interval=30)
            self._connected.clear()
            if not self._stop:
                log.info("disconnected; reconnecting in %ss", RECONNECT_DELAY_S)
                time.sleep(RECONNECT_DELAY_S)

    def _on_open(self, _ws):
        self._connected.set()
        threading.Thread(target=self._spawn, daemon=True).start()

    def _spawn(self):
        res = self.send_action("spawn", {"mapId": self.cfg["spawn_map_id"]})
        log.info("spawn -> %s", res)

    def _on_close(self, _ws, _code, _msg):
        self._connected.clear()
        for waiter in list(self._pending.values()):
            waiter["result"] = {"status": "failed", "reason": "disconnected"}
            waiter["event"].set()
        self._pending.clear()

    # ---- inbound ----

    def _on_message(self, _ws, raw):
        try:
            msg = json.loads(raw)
        except ValueError:
            return
        mtype = msg.get("type")
        if mtype == "snapshot":
            snap = msg.get("data") or {}
            self.store.update_snapshot(snap)
            self._reflex(snap)
        elif mtype == "event":
            name = msg.get("event", "")
            data = msg.get("data") or {}
            if name == "chat":
                self.store.add_chat(data.get("senderName", "?"), data.get("text", ""))
            if name == "died":
                threading.Timer(RESPAWN_DELAY_S, self._spawn).start()
            self.store.add_event(name, data)
        elif mtype in ("action_done", "action_failed"):
            waiter = self._pending.pop(msg.get("seq", 0), None)
            if waiter is not None:
                if mtype == "action_done":
                    waiter["result"] = {"status": "success", "reason": ""}
                else:
                    waiter["result"] = {"status": "failed", "reason": msg.get("reason", "")}
                waiter["event"].set()

    # ---- reflex (agent not involved) ----

    def _reflex(self, snap: dict):
        hp, max_hp = snap.get("hp", 0), snap.get("maxHp", 0)
        if max_hp <= 0 or hp <= 0:
            return
        if hp > max_hp * self.cfg["hp_threshold"]:
            return
        now = time.monotonic()
        if now - self._last_potion < POTION_COOLDOWN_S:
            return
        self._last_potion = now
        threading.Thread(
            target=self.send_action,
            args=("use_item", {"itemId": self.cfg["potion_item_id"]}),
            daemon=True,
        ).start()