from typing import Optional, Dict, Any, List

from config import Config
from intent_schema import INTENT_SCHEMA, ValidationError, validate_response
from persona import SYSTEM_PROMPT, compress_state


class Brain:
    def __init__(self, config: Config):
        self._client = None
        self.config = config
        self.memory: List[Dict[str, str]] = []
        self.persona = config.persona

    @property
    def client(self):
        if self._client is None:
            from openai import OpenAI
            self._client = OpenAI(base_url=self.config.base_url, api_key=self.config.api_key)
        return self._client

    def think(self, state: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        user_msg = compress_state(state)
        self.memory.append({"role": "user", "content": user_msg})
        self._trim_memory()

        messages = [{"role": "system", "content": SYSTEM_PROMPT.format(**self.persona)}]
        messages += self.memory[-self.config.memory_window:]

        try:
            return self._call_llm(messages)
        except ValidationError as e:
            error_msg = f"Invalid: {e}. Try again."
            self.memory.append({"role": "user", "content": error_msg})
            self._trim_memory()
            retry_messages = [{"role": "system", "content": SYSTEM_PROMPT.format(**self.persona)}]
            retry_messages += self.memory[-self.config.memory_window:]
            try:
                return self._call_llm(retry_messages)
            except ValidationError:
                self.memory.pop()
                return None
        except Exception:
            self.memory.pop()
            return None

    def _call_llm(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        response = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            tools=[INTENT_SCHEMA],
            tool_choice="auto",
        )
        return validate_response(response)

    def append_event(self, event_name: str) -> None:
        self.memory.append({"role": "system", "content": f"Event: {event_name}"})
        self._trim_memory()

    def reset(self) -> None:
        self.memory.clear()

    def _trim_memory(self) -> None:
        if len(self.memory) > self.config.memory_window * 2:
            del self.memory[:-self.config.memory_window]