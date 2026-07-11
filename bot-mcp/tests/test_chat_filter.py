import pytest
from botmcp.chat_filter import prepare_chat, ChatBlockedError


def test_ascii_passthrough():
    assert prepare_chat("hello world") == "hello world"

def test_strips_whitespace():
    assert prepare_chat("  hi  ") == "hi"

@pytest.mark.parametrize("bad", ["@ban someone", "!kill", "/help"])
def test_blocked_prefixes(bad):
    with pytest.raises(ChatBlockedError) as e:
        prepare_chat(bad)
    assert e.value.reason == "blocked_prefix"

def test_empty_raises():
    with pytest.raises(ChatBlockedError) as e:
        prepare_chat("   ")
    assert e.value.reason == "empty_message"

def test_truncates_ascii_to_70_bytes():
    out = prepare_chat("x" * 100)
    assert out == "x" * 70

def test_multibyte_never_split():
    out = prepare_chat("好" * 40)
    assert out == "好" * 35
    assert len(out.encode("big5")) == 70

def test_mixed_boundary_drops_half_char():
    out = prepare_chat("a" + "好" * 40)
    assert out == "a" + "好" * 34
    assert len(out.encode("big5")) == 69

def test_unencodable_char_replaced():
    assert prepare_chat("héllo") == "h?llo"  # é not in Big5