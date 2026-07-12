import time
from typing import Optional, Dict, Any

from config import Config
from websocket_client import WebSocketClient
from reflex_layer import ReflexLayer
from brain import Brain

_seq_counter = 1


def next_seq() -> int:
    global _seq_counter
    s = _seq_counter
    _seq_counter += 1
    return s


def reconnect_with_backoff(config: Config) -> WebSocketClient:
    delay = 1.0
    for attempt in range(5):
        print(f"[sidecar] reconnect attempt {attempt + 1}/5 in {delay:.1f}s...")
        time.sleep(delay)
        ws = WebSocketClient(config.ws_url)
        try:
            ws.connect()
            print("[sidecar] reconnected")
            return ws
        except Exception as e:
            print(f"[sidecar] reconnect failed: {e}")
            delay = min(delay * 2, 30.0)
    print("[sidecar] max retries exceeded — exiting")
    exit(1)


def main() -> None:
    config = Config.load("config.yaml")

    print(f"[sidecar] connecting to {config.ws_url}")
    ws = WebSocketClient(config.ws_url)
    try:
        ws.connect()
    except Exception as e:
        print(f"[sidecar] connection failed: {e}")
        return

    reflex = ReflexLayer(config)
    brain = Brain(config)
    current_state: Optional[Dict[str, Any]] = None
    last_brain_time = 0.0

    in_flight: Dict[int, tuple] = {}
    _do_spawn(ws, config, in_flight)

    while True:
        msg = ws.recv(timeout=1.0)

        if msg is None:
            if not ws.is_connected():
                ws = reconnect_with_backoff(config)
                reflex.reset()
                brain.reset()
                current_state = None
                in_flight.clear()
                _do_spawn(ws, config, in_flight)
                continue

            if current_state is not None:
                action = reflex.should_act(current_state)
                if action:
                    s = next_seq()
                    ws.send({"action": action["action"], "args": action["args"], "seq": s})
                    in_flight[s] = (action["action"], action["args"])
                    print(f"[sidecar] reflex -> {action['action']} seq={s}")
            continue

        msg_type = msg.get("type")

        if msg_type == "snapshot":
            current_state = msg.get("data")

            reflex_action = reflex.should_act(current_state)
            if reflex_action:
                s = next_seq()
                ws.send({"action": reflex_action["action"], "args": reflex_action["args"], "seq": s})
                in_flight[s] = (reflex_action["action"], reflex_action["args"])
                print(f"[sidecar] reflex -> {reflex_action['action']} seq={s}")

            now = time.time()
            if now - last_brain_time >= config.brain_interval_seconds:
                last_brain_time = now
                brain_action = brain.think(current_state)
                if brain_action:
                    s = next_seq()
                    ws.send({"action": brain_action["action"], "args": brain_action["args"], "seq": s})
                    in_flight[s] = (brain_action["action"], brain_action["args"])
                    print(f"[sidecar] brain -> {brain_action['action']} seq={s}")

        elif msg_type == "event":
            event_data = msg.get("data", {})
            event_name = event_data.get("event", "")
            brain.append_event(event_data)
            if event_name == "died":
                reflex.reset()
                brain.reset()
                current_state = None
            print(f"[sidecar] event: {event_name}")

        elif msg_type == "action_done":
            seq = msg.get("seq", 0)
            info = in_flight.pop(seq, None)
            action_name = info[0] if info else "?"
            print(f"[sidecar] action_done: seq={seq} action={action_name}")

            if info and info[0] == "pickup":
                drop_id = info[1].get("dropId")
                if drop_id is not None:
                    reflex.clear_in_flight(drop_id)

        elif msg_type == "action_failed":
            seq = msg.get("seq", 0)
            info = in_flight.pop(seq, None)
            action_name = info[0] if info else "?"
            reason = msg.get("reason", "")
            print(f"[sidecar] action_failed: seq={seq} action={action_name} reason={reason}")
            if info:
                brain.append_action_failed(action_name, reason)

            if info and info[0] == "pickup":
                drop_id = info[1].get("dropId")
                if drop_id is not None:
                    reflex.clear_in_flight(drop_id)


def _do_spawn(ws: WebSocketClient, config: Config, in_flight: Dict[int, tuple]) -> None:
    global _seq_counter
    _seq_counter = 1
    spawn_seq = next_seq()
    ws.send({"action": "spawn", "args": {"mapId": config.spawn_map_id}, "seq": spawn_seq})
    in_flight[spawn_seq] = ("spawn", {"mapId": config.spawn_map_id})
    print(f"[sidecar] sent spawn mapId={config.spawn_map_id} seq={spawn_seq}")


if __name__ == "__main__":
    main()