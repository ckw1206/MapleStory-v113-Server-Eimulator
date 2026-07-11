"""Outbound chat filter: Big5 70-byte cap without splitting chars, command-prefix reject."""

MAX_BYTES = 70
BLOCKED_PREFIXES = ("@", "!", "/")


class ChatBlockedError(ValueError):
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def prepare_chat(text: str) -> str:
    text = text.strip()
    if not text:
        raise ChatBlockedError("empty_message")
    if text.startswith(BLOCKED_PREFIXES):
        raise ChatBlockedError("blocked_prefix")
    encoded = text.encode("big5", errors="replace")
    if len(encoded) <= MAX_BYTES:
        return encoded.decode("big5")
    return encoded[:MAX_BYTES].decode("big5", errors="ignore")