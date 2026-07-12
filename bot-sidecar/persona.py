SYSTEM_PROMPT = """You are {name}, a friendly companion bot in MapleStory.
You fight alongside real players, chat in-character, and help with farming.
You have the following actions available: move_to, attack, pickup, use_item, say, face, idle.
Only use the bot_action tool to respond.
Personality: {greeting}
"""


def compress_state(state: dict) -> str:
    pos = state.get("position", {})
    lines = [
        f"Map {state.get('mapId', '?')} at position ({pos.get('x', 0)}, {pos.get('y', 0)})",
        f"HP: {state.get('hp', 0)}/{state.get('maxHp', 1)}  MP: {state.get('mp', 0)}/{state.get('maxMp', 1)}  Level: {state.get('level', '?')}",
        f"Mobs nearby: {len(state.get('mobs', []))}",
        f"Drops nearby: {len(state.get('drops', []))}",
        f"Players nearby: {[p['name'] for p in state.get('players', [])]}",
    ]
    return "\n".join(lines)