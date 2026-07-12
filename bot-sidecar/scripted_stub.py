import time
from typing import Optional, Dict, Any, List

from config import Config
from websocket_client import WebSocketClient

_seq_counter = 1


def next_seq() -> int:
    global _seq_counter
    s = _seq_counter
    _seq_counter += 1
    return s


def main() -> None:
    config = Config.load("config.yaml")
    ws = WebSocketClient(config.ws_url)

    print(f"[stub] connecting to {config.ws_url}")
    try:
        ws.connect()
    except Exception as e:
        print(f"[stub] connection failed: {e}")
        return

    spawn_seq = next_seq()
    ws.send({"action": "spawn", "args": {"mapId": config.spawn_map_id}, "seq": spawn_seq})
    print(f"[stub] sent spawn mapId={config.spawn_map_id} seq={spawn_seq}")

    current_state: Optional[Dict[str, Any]] = None
    last_mob_oid: Optional[int] = None
    last_drop_oid: Optional[int] = None

    time.sleep(2)

    # Consume initial messages to get a snapshot
    for _ in range(5):
        msg = ws.recv(timeout=2.0)
        if msg is None:
            break
        print(f"[stub] recv: {msg}")
        if msg.get("type") == "snapshot":
            current_state = msg.get("data")
            mobs = current_state.get("mobs", [])
            drops = current_state.get("drops", [])
            if mobs:
                last_mob_oid = mobs[0].get("oid")
            if drops:
                last_drop_oid = drops[0].get("oid")

    # move_to
    s = next_seq()
    ws.send({"action": "move_to", "args": {"x": 100, "y": 200}, "seq": s})
    print(f"[stub] sent move_to seq={s}")
    _print_messages(ws, count=3)

    # attack (if mob available)
    if last_mob_oid is not None:
        s = next_seq()
        ws.send({"action": "attack", "args": {"mobId": last_mob_oid}, "seq": s})
        print(f"[stub] sent attack mobId={last_mob_oid} seq={s}")
    else:
        print("[stub] SKIP attack — no mob in snapshot")
    _print_messages(ws, count=3)

    # pickup (if drop available)
    if last_drop_oid is not None:
        s = next_seq()
        ws.send({"action": "pickup", "args": {"dropId": last_drop_oid}, "seq": s})
        print(f"[stub] sent pickup dropId={last_drop_oid} seq={s}")
    else:
        print("[stub] SKIP pickup — no drop in snapshot")
    _print_messages(ws, count=3)

    # say
    s = next_seq()
    ws.send({"action": "say", "args": {"text": "Hello from the stub!"}, "seq": s})
    print(f"[stub] sent say seq={s}")
    _print_messages(ws, count=3)

    ws.close()
    print("[stub] done")


def _print_messages(ws: WebSocketClient, count: int) -> None:
    for _ in range(count):
        msg = ws.recv(timeout=2.0)
        if msg is None:
            break
        print(f"[stub] recv: {msg}")


if __name__ == "__main__":
    main()