import pytest
from unittest.mock import MagicMock
from intent_schema import validate_response, ValidationError, VALID_ACTIONS


def _make_response(action: str, args: str):
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


def test_valid_tool_call_response():
    response = _make_response("move_to", '{"x":10,"y":20}')
    result = validate_response(response)
    assert result["action"] == "move_to"
    assert result["args"] == {"x": 10, "y": 20}


def test_invalid_action_raises():
    response = _make_response("dance", "{}")
    with pytest.raises(ValidationError) as exc:
        validate_response(response)
    assert "invalid action" in str(exc.value)


def test_no_tool_calls_raises():
    mock_response = MagicMock()
    mock_choice = MagicMock()
    mock_message = MagicMock()
    mock_message.tool_calls = []
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]
    response = mock_response
    with pytest.raises(ValidationError) as exc:
        validate_response(response)
    assert "no tool_calls" in str(exc.value)


def test_valid_actions_cover_all_non_spawn():
    expected = {"move_to", "attack", "pickup", "use_item", "say", "face", "idle"}
    assert VALID_ACTIONS == expected