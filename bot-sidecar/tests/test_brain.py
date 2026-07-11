import pytest
from unittest.mock import MagicMock, patch
from brain import Brain
from intent_schema import ValidationError


def _make_mock_response(action: str, args: str):
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_tool_call = MagicMock()
    mock_func = MagicMock()
    mock_func.name = "bot_action"
    mock_func.arguments = f'{{"action":"{action}","args":{args}}}'
    mock_tool_call.function = mock_func
    mock_message.tool_calls = [mock_tool_call]
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    return mock_response


def test_brain_returns_action_dict():
    config = MagicMock()
    config.base_url = "http://localhost:11434/v1"
    config.api_key = "test"
    config.model = "llama3"
    config.memory_window = 20
    config.persona = {"name": "TestBot", "greeting": "Hi"}

    state = {
        "mapId": 100000000,
        "position": {"x": 0, "y": 0},
        "hp": 500,
        "maxHp": 1000,
        "mp": 200,
        "maxMp": 300,
        "level": 30,
        "mobs": [],
        "drops": [],
        "players": [],
    }

    mock_response = _make_mock_response("idle", "{}")

    with patch("openai.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        MockOpenAI.return_value = mock_client

        brain = Brain(config)
        result = brain.think(state)

    assert result is not None
    assert result["action"] == "idle"
    assert isinstance(result["args"], dict)


def test_brain_retry_on_validation_error():
    config = MagicMock()
    config.base_url = "http://localhost:11434/v1"
    config.api_key = "test"
    config.model = "llama3"
    config.memory_window = 20
    config.persona = {"name": "TestBot", "greeting": "Hi"}

    state = {
        "mapId": 100000000,
        "position": {"x": 0, "y": 0},
        "hp": 500,
        "maxHp": 1000,
        "mp": 200,
        "maxMp": 300,
        "level": 30,
        "mobs": [],
        "drops": [],
        "players": [],
    }

    bad_response = MagicMock()
    bad_choice = MagicMock()
    bad_message = MagicMock()
    bad_message.tool_calls = []
    bad_choice.message = bad_message
    bad_response.choices = [bad_choice]

    good_response = _make_mock_response("idle", "{}")

    with patch("openai.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [bad_response, good_response]
        MockOpenAI.return_value = mock_client

        brain = Brain(config)
        result = brain.think(state)

    assert result is not None
    assert result["action"] == "idle"


def test_brain_returns_none_on_llm_exception():
    config = MagicMock()
    config.base_url = "http://localhost:11434/v1"
    config.api_key = "test"
    config.model = "llama3"
    config.memory_window = 20
    config.persona = {"name": "TestBot", "greeting": "Hi"}

    state = {
        "mapId": 100000000,
        "position": {"x": 0, "y": 0},
        "hp": 500,
        "maxHp": 1000,
        "mp": 200,
        "maxMp": 300,
        "level": 30,
        "mobs": [],
        "drops": [],
        "players": [],
    }

    with patch("openai.OpenAI") as MockOpenAI:
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("network error")
        MockOpenAI.return_value = mock_client

        brain = Brain(config)
        result = brain.think(state)

    assert result is None


def test_brain_retry_includes_error_feedback_in_messages():
    config = MagicMock()
    config.base_url = "http://localhost:11434/v1"
    config.api_key = "test"
    config.model = "llama3"
    config.memory_window = 20
    config.persona = {"name": "TestBot", "greeting": "Hi"}

    state = {
        "mapId": 100000000,
        "position": {"x": 0, "y": 0},
        "hp": 500,
        "maxHp": 1000,
        "mp": 200,
        "maxMp": 300,
        "level": 30,
        "mobs": [],
        "drops": [],
        "players": [],
    }

    bad_response = MagicMock()
    bad_choice = MagicMock()
    bad_message = MagicMock()
    bad_message.tool_calls = []
    bad_choice.message = bad_message
    bad_response.choices = [bad_choice]

    good_response = _make_mock_response("idle", "{}")

    captured_messages = []

    with patch("openai.OpenAI") as MockOpenAI:
        mock_client = MagicMock()

        def capture_create(**kwargs):
            captured_messages.append(kwargs.get("messages"))
            if len(captured_messages) == 1:
                return bad_response
            return good_response

        mock_client.chat.completions.create.side_effect = capture_create
        MockOpenAI.return_value = mock_client

        brain = Brain(config)
        result = brain.think(state)

    assert result is not None
    # First call had no error feedback, second call had "Invalid: ..." in user message
    assert len(captured_messages) == 2
    second_messages = captured_messages[1]
    second_user_contents = [m["content"] for m in second_messages if m.get("role") == "user"]
    assert any("Invalid:" in c for c in second_user_contents), (
        f"Retry messages should contain 'Invalid:' feedback. Got: {second_messages}"
    )