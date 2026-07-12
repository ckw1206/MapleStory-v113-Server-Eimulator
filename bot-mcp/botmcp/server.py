"""MCP server exposing the 3-tool surface. Pure logic is module-level for testability."""

import os

import yaml
from mcp.server.fastmcp import FastMCP

from .chat_filter import ChatBlockedError, prepare_chat
from .state import StateStore
from .ws_client import BotClient

EMOTES = {"F1": 1, "F2": 2, "F3": 3, "F4": 4, "F5": 5, "F6": 6, "F7": 7}


def job_name(job_id: int) -> str:
    if job_id == 0:
        return "beginner"
    for lo, hi, name in ((100, 199, "warrior"), (200, 299, "magician"),
                         (300, 399, "bowman"), (400, 499, "thief"), (500, 599, "pirate")):
        if lo <= job_id <= hi:
            return name
    return "gm" if job_id >= 900 else "beginner"


def load_config() -> dict:
    default = os.path.join(os.path.dirname(__file__), "..", "config.yaml")
    path = os.environ.get("BOTMCP_CONFIG", default)
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def build_payload(store: StateStore) -> dict:
    snap = store.snapshot() or {}
    pos = snap.get("position") or {}
    return {
        "bot_status": {
            "name": snap.get("name", ""),
            "job": job_name(snap.get("job", 0)),
            "level": snap.get("level", 0),
            "hp": snap.get("hp", 0), "max_hp": snap.get("maxHp", 0),
            "mp": snap.get("mp", 0), "max_mp": snap.get("maxMp", 0),
            "mesos": snap.get("mesos", 0),
            "map_id": snap.get("mapId", 0),
            "x": pos.get("x", 0), "y": pos.get("y", 0),
        },
        "nearby_entities": {
            "players": snap.get("players", []),
            "monsters": [
                {"oid": m["oid"], "mob_id": m["id"], "x": m["x"], "y": m["y"], "hp_pct": m["hpPct"]}
                for m in snap.get("mobs", [])
            ],
            "drops": [
                {"oid": d["oid"], "item_id": d["itemId"], "x": d["x"], "y": d["y"]}
                for d in snap.get("drops", [])
            ],
            "portals": snap.get("portals", []),
        },
        "chat_history": store.chat_history(),
        "pending_events": [
            e["event"] + (f": {e['data']}" if e["data"] else "")
            for e in store.drain_events()
        ],
    }


def perform_act(client, action: str, x: int | None = None, y: int | None = None,
                target_oid: int | None = None, item_id: int | None = None,
                chat_message: str | None = None, emote: str | None = None) -> dict:
    results = []

    if chat_message:
        try:
            results.append(("say", client.send_action("say", {"text": prepare_chat(chat_message)})))
        except ChatBlockedError as e:
            results.append(("say", {"status": "failed", "reason": e.reason}))

    if emote and emote != "none":
        if emote in EMOTES:
            results.append(("face", client.send_action("face", {"expressionId": EMOTES[emote]})))
        else:
            results.append(("face", {"status": "failed", "reason": "unknown_emote"}))

    if action == "idle":
        results.append(("idle", client.send_action("idle", {})))
    elif action == "move_to":
        if x is None or y is None:
            results.append(("move_to", {"status": "failed", "reason": "move_to requires x and y"}))
        else:
            results.append(("move_to", client.send_action("move_to", {"x": x, "y": y})))
    elif action == "attack":
        if target_oid is None:
            results.append(("attack", {"status": "failed", "reason": "attack requires target_oid"}))
        else:
            results.append(("attack", client.send_action("attack", {"mobId": target_oid})))
    elif action == "pickup":
        if target_oid is None:
            results.append(("pickup", {"status": "failed", "reason": "pickup requires target_oid"}))
        else:
            results.append(("pickup", client.send_action("pickup", {"dropId": target_oid})))
    elif action == "use_item":
        if item_id is None:
            results.append(("use_item", {"status": "failed", "reason": "use_item requires item_id"}))
        else:
            results.append(("use_item", client.send_action("use_item", {"itemId": item_id})))
    else:
        results.append((action, {"status": "failed", "reason": f"unknown_action: {action}"}))

    failures = [f"{name}: {r['reason']}" for name, r in results if r["status"] != "success"]
    parts = {name: r for name, r in results}
    if failures and len(failures) < len(results):
        status = "partial"
    elif failures:
        status = "failed"
    else:
        status = "success"
    return {"status": status, "parts": parts, "reason": "; ".join(failures)}


def main():
    cfg = load_config()
    store = StateStore()
    client = BotClient(cfg, store)
    client.start()

    mcp = FastMCP("maplestory-bot")

    @mcp.tool()
    def bot_perceive() -> dict:
        """Current world state: your status, nearby players/monsters/drops/portals, recent chat, pending events."""
        return build_payload(store)

    @mcp.tool()
    def bot_act(action: str, x: int | None = None, y: int | None = None,
                target_oid: int | None = None, item_id: int | None = None,
                chat_message: str | None = None, emote: str | None = None) -> dict:
        """One game turn. action: idle | move_to(x,y) | attack(target_oid) | pickup(target_oid) | use_item(item_id).
        Optional chat_message (map chat, ~70 bytes max) and emote (F1-F7). Order: say -> emote -> action.
        Returns {status, parts, reason} where status is 'success' | 'partial' | 'failed'.
        'partial' means some sub-actions succeeded and some failed; parts is {name: result}."""
        return perform_act(client, action, x=x, y=y, target_oid=target_oid,
                           item_id=item_id, chat_message=chat_message, emote=emote)

    @mcp.tool()
    def bot_wait(timeout_s: int = 30) -> dict:
        """Sleep until something notable happens (player chat, damaged, mob killed, died) or timeout.
        Returns a fresh perceive payload plus wake_reason. Max 120s."""
        reason = store.wait_for_event(min(max(timeout_s, 1), 120))
        payload = build_payload(store)
        payload["wake_reason"] = reason
        return payload

    mcp.run()