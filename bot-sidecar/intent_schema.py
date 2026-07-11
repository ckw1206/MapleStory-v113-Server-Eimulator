from typing import Dict, Any

INTENT_SCHEMA = {
    "type": "function",
    "function": {
        "name": "bot_action",
        "description": "Perform a game action",
        "parameters": {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["move_to", "attack", "pickup", "use_item", "say", "face", "idle"],
                },
                "args": {
                    "type": "object",
                },
            },
            "required": ["action", "args"],
        },
    },
}

VALID_ACTIONS = {"move_to", "attack", "pickup", "use_item", "say", "face", "idle"}


class ValidationError(Exception):
    pass


def validate_response(response) -> Dict[str, Any]:
    try:
        choice = response.choices[0]
        message = choice.message
        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            raise ValidationError("no tool_calls in response")
        func = tool_calls[0].function
        if func.name != "bot_action":
            raise ValidationError(f"unexpected function name: {func.name}")
        args = _parse_args(func.arguments)
        if "args" not in args:
            args["args"] = {}
        elif not isinstance(args["args"], dict):
            raise ValidationError("args is not a dict")
        action = args.get("action")
        if action not in VALID_ACTIONS:
            raise ValidationError(f"invalid action: {action}")
        return args
    except (AttributeError, IndexError, KeyError) as e:
        raise ValidationError(str(e)) from e


def _parse_args(arguments: str) -> Dict[str, Any]:
    import json
    try:
        return json.loads(arguments)
    except json.JSONDecodeError as e:
        raise ValidationError(f"bad JSON in function arguments: {e}") from e