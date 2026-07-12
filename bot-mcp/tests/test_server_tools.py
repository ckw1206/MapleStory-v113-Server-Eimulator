from botmcp.server import build_payload, perform_act, job_name
from botmcp.state import StateStore


class DummyClient:
    def __init__(self, fail_actions=()):
        self.calls = []
        self.fail_actions = set(fail_actions)

    def send_action(self, action, args=None, timeout=10.0):
        self.calls.append((action, args))
        if action in self.fail_actions:
            return {"status": "failed", "reason": f"{action}_boom"}
        return {"status": "success", "reason": ""}


SNAP = {
    "name": "Fatty", "job": 112, "mesos": 1234, "mapId": 100000000,
    "position": {"x": 10, "y": -5}, "hp": 300, "maxHp": 500, "mp": 50, "maxMp": 100,
    "level": 42,
    "mobs": [{"id": 100100, "oid": 7, "x": 1, "y": 2, "hpPct": 80}],
    "drops": [{"oid": 9, "itemId": 2000002, "x": 3, "y": 4}],
    "players": [{"id": 2, "name": "kyle", "x": 5, "y": 6}],
    "portals": [{"name": "sp", "x": 0, "y": 0}],
}


def test_job_name_ranges():
    assert job_name(0) == "beginner"
    assert job_name(112) == "warrior"
    assert job_name(230) == "magician"
    assert job_name(312) == "bowman"
    assert job_name(412) == "thief"
    assert job_name(520) == "pirate"
    assert job_name(910) == "gm"

def test_build_payload_maps_snapshot():
    store = StateStore()
    store.update_snapshot(SNAP)
    store.add_chat("kyle", "hi")
    store.add_event("mob_killed", {"oid": 7})
    p = build_payload(store)
    assert p["bot_status"] == {
        "name": "Fatty", "job": "warrior", "level": 42, "hp": 300, "max_hp": 500,
        "mp": 50, "max_mp": 100, "mesos": 1234, "map_id": 100000000, "x": 10, "y": -5,
    }
    assert p["nearby_entities"]["monsters"] == [{"oid": 7, "mob_id": 100100, "x": 1, "y": 2, "hp_pct": 80}]
    assert p["nearby_entities"]["drops"] == [{"oid": 9, "item_id": 2000002, "x": 3, "y": 4}]
    assert p["chat_history"][0]["message"] == "hi"
    assert p["pending_events"] == ["mob_killed: {'oid': 7}"]
    # events drained
    assert build_payload(store)["pending_events"] == []

def test_build_payload_before_first_snapshot():
    p = build_payload(StateStore())
    assert p["bot_status"]["name"] == ""
    assert p["nearby_entities"]["monsters"] == []

def test_act_fanout_order_say_face_action():
    c = DummyClient()
    r = perform_act(c, "attack", target_oid=7, chat_message="打死你", emote="F3")
    assert [a for a, _ in c.calls] == ["say", "face", "attack"]
    assert c.calls[0][1] == {"text": "打死你"}
    assert c.calls[1][1] == {"expressionId": 3}
    assert c.calls[2][1] == {"mobId": 7}
    assert r["status"] == "success"
    assert r["parts"]["say"] == {"status": "success", "reason": ""}
    assert r["parts"]["face"] == {"status": "success", "reason": ""}
    assert r["parts"]["attack"] == {"status": "success", "reason": ""}

def test_act_arg_mapping():
    c = DummyClient()
    assert perform_act(c, "move_to", x=100, y=-20)["status"] == "success"
    assert perform_act(c, "pickup", target_oid=9)["status"] == "success"
    assert perform_act(c, "use_item", item_id=2000002)["status"] == "success"
    assert perform_act(c, "idle")["status"] == "success"
    assert c.calls == [
        ("move_to", {"x": 100, "y": -20}),
        ("pickup", {"dropId": 9}),
        ("use_item", {"itemId": 2000002}),
        ("idle", {}),
    ]

def test_act_missing_args_fail_without_sending():
    c = DummyClient()
    assert perform_act(c, "move_to")["status"] == "failed"
    assert perform_act(c, "attack")["status"] == "failed"
    assert perform_act(c, "use_item")["status"] == "failed"
    assert perform_act(c, "warp")["status"] == "failed"
    assert c.calls == []

def test_act_blocked_chat_still_runs_action():
    c = DummyClient()
    r = perform_act(c, "idle", chat_message="@gm hello")
    assert c.calls == [("idle", {})]        # say never sent
    assert r["status"] == "partial"
    assert r["parts"]["say"]["status"] == "failed"
    assert "blocked_prefix" in r["parts"]["say"]["reason"]
    assert r["parts"]["idle"] == {"status": "success", "reason": ""}

def test_act_aggregates_failures():
    c = DummyClient(fail_actions={"attack"})
    r = perform_act(c, "attack", target_oid=7, chat_message="hi")
    assert r["status"] == "partial"
    assert r["parts"]["say"]["status"] == "success"
    assert r["parts"]["attack"]["status"] == "failed"
    assert "attack_boom" in r["reason"]


def test_perform_act_all_fail_is_failed():
    c = DummyClient(fail_actions={"move_to", "say"})
    r = perform_act(c, "move_to", x=0, y=0, chat_message="x")
    assert r["status"] == "failed"
    assert r["parts"]["say"]["status"] == "failed"
    assert r["parts"]["move_to"]["status"] == "failed"


def test_perform_act_all_success_is_success():
    c = DummyClient()
    r = perform_act(c, "move_to", x=10, y=-5)
    assert r["status"] == "success"
    assert r["parts"]["move_to"]["status"] == "success"


def test_perform_act_partial_when_mixed():
    c = DummyClient(fail_actions={"face"})
    r = perform_act(c, "idle", emote="F1")
    assert r["status"] == "partial"
    assert r["parts"]["face"]["status"] == "failed"