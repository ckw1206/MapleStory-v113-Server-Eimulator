from typing import Optional, Dict, Any, Set

from config import Config


class ReflexLayer:
    def __init__(self, config: Config):
        self.hp_crisis_threshold = 0.30
        self.potion_item_id = config.potion_item_id
        self._in_flight: Set[int] = set()

    def should_act(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        # HP crisis potion — only if we actually have the potion
        hp = state.get("hp", 0)
        max_hp = state.get("maxHp", 1)
        if max_hp <= 0:
            max_hp = 1
        if hp / max_hp < self.hp_crisis_threshold:
            if self._potion_available(state):
                return {"action": "use_item", "args": {"itemId": self.potion_item_id}}

        # Auto-loot: first drop not already in-flight
        drops = state.get("drops", [])
        for drop in drops:
            oid = drop.get("oid")
            if oid is not None and oid not in self._in_flight:
                self._in_flight.add(oid)
                return {"action": "pickup", "args": {"dropId": oid}}

        return None

    def _potion_available(self, state: Dict[str, Any]) -> bool:
        inv = state.get("inventorySummary", [])
        for item in inv:
            if item.get("id") == self.potion_item_id:
                return True
        return False

    def clear_in_flight(self, drop_id: int) -> None:
        self._in_flight.discard(drop_id)

    def reset(self) -> None:
        self._in_flight.clear()