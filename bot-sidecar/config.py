from dataclasses import dataclass, field
from typing import Optional
import os
import yaml


@dataclass
class Config:
    ws_url: str
    base_url: str
    api_key: str
    model: str
    brain_interval_seconds: int
    potion_item_id: int
    spawn_map_id: int
    memory_window: int
    persona: dict

    @staticmethod
    def load(path: str = "config.yaml") -> "Config":
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        return Config(
            ws_url=os.environ.get("BOT_WS_URL", data.get("ws_url", "ws://127.0.0.1:9999/ws?token=changeme")),
            base_url=os.environ.get("BOT_LLM_BASE_URL", data.get("base_url", "http://localhost:11434/v1")),
            api_key=os.environ.get("BOT_LLM_API_KEY", data.get("api_key", "ollama")),
            model=os.environ.get("BOT_LLM_MODEL", data.get("model", "llama3")),
            brain_interval_seconds=int(os.environ.get("BOT_BRAIN_INTERVAL_SECONDS", str(data.get("brain_interval_seconds", 5)))),
            potion_item_id=int(os.environ.get("BOT_POTION_ITEM_ID", str(data.get("potion_item_id", 2000002)))),
            spawn_map_id=int(os.environ.get("BOT_SPAWN_MAP_ID", str(data.get("spawn_map_id", 100000000)))),
            memory_window=int(os.environ.get("BOT_MEMORY_WINDOW", str(data.get("memory_window", 20)))),
            persona=data.get("persona", {"name": "Buddy", "greeting": "Hi! I'm here to help you farm."}),
        )