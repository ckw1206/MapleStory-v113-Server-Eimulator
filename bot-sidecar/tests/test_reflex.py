import pytest
from unittest.mock import MagicMock
from reflex_layer import ReflexLayer


def make_config(potion_item_id: int = 2000002) -> MagicMock:
    c = MagicMock()
    c.potion_item_id = potion_item_id
    return c


def test_hp_20pct_returns_potion():
    config = make_config()
    reflex = ReflexLayer(config)
    state = {
        "hp": 100,
        "maxHp": 500,
        "inventorySummary": [{"id": 2000002, "type": "USE", "qty": 5}],
        "drops": [],
    }
    result = reflex.should_act(state)
    assert result is not None
    assert result["action"] == "use_item"
    assert result["args"]["itemId"] == 2000002


def test_hp_50pct_returns_none():
    config = make_config()
    reflex = ReflexLayer(config)
    state = {
        "hp": 500,
        "maxHp": 1000,
        "inventorySummary": [{"id": 2000002, "type": "USE", "qty": 5}],
        "drops": [],
    }
    result = reflex.should_act(state)
    assert result is None


def test_potion_not_in_inventory_returns_none():
    config = make_config()
    reflex = ReflexLayer(config)
    state = {
        "hp": 50,
        "maxHp": 1000,
        "inventorySummary": [],
        "drops": [],
    }
    result = reflex.should_act(state)
    assert result is None


def test_loot_first_drop_returns_pickup():
    config = make_config()
    reflex = ReflexLayer(config)
    state = {
        "hp": 500,
        "maxHp": 1000,
        "inventorySummary": [],
        "drops": [{"oid": 9, "itemId": 4001000, "x": 50, "y": 60}],
    }
    result = reflex.should_act(state)
    assert result is not None
    assert result["action"] == "pickup"
    assert result["args"]["dropId"] == 9


def test_loot_second_call_returns_none_in_flight():
    config = make_config()
    reflex = ReflexLayer(config)
    state = {
        "hp": 500,
        "maxHp": 1000,
        "inventorySummary": [],
        "drops": [{"oid": 9, "itemId": 4001000, "x": 50, "y": 60}],
    }
    result1 = reflex.should_act(state)
    assert result1 is not None
    assert result1["args"]["dropId"] == 9

    result2 = reflex.should_act(state)
    assert result2 is None


def test_in_flight_cleared_on_clear_in_flight():
    config = make_config()
    reflex = ReflexLayer(config)
    state = {
        "hp": 500,
        "maxHp": 1000,
        "inventorySummary": [],
        "drops": [{"oid": 9, "itemId": 4001000, "x": 50, "y": 60}],
    }
    reflex.should_act(state)
    reflex.clear_in_flight(9)
    result = reflex.should_act(state)
    assert result is not None
    assert result["args"]["dropId"] == 9


def test_reset_clears_in_flight():
    config = make_config()
    reflex = ReflexLayer(config)
    state = {
        "hp": 500,
        "maxHp": 1000,
        "inventorySummary": [],
        "drops": [{"oid": 9, "itemId": 4001000, "x": 50, "y": 60}],
    }
    reflex.should_act(state)
    reflex.reset()
    result = reflex.should_act(state)
    assert result is not None
    assert result["args"]["dropId"] == 9