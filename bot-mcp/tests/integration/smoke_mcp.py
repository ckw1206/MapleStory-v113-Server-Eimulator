"""End-to-end smoke: drives bot-mcp over real MCP stdio against a running game server.

Usage:  cd bot-mcp && python tests/integration/smoke_mcp.py
Requires: docker compose up -d, seeded bot char, config.yaml with real token.
"""

import asyncio
import json
import os
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def unwrap(result):
    return json.loads(result.content[0].text)


async def main():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "botmcp"],
        env={**os.environ, "BOTMCP_CONFIG": os.path.abspath("config.yaml")},
    )
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as s:
            await s.initialize()

            tools = [t.name for t in (await s.list_tools()).tools]
            assert sorted(tools) == ["bot_act", "bot_perceive", "bot_wait"], tools
            print("PASS tool surface:", tools)

            await asyncio.sleep(4)  # allow WS connect + auto-spawn + first snapshot

            p = unwrap(await s.call_tool("bot_perceive", {}))
            st = p["bot_status"]
            assert st["map_id"] != 0, "no snapshot — did auto-spawn run?"
            assert st["name"], "snapshot missing name (Task 4 deployed?)"
            print(f"PASS perceive: {st['name']} lv{st['level']} {st['job']} @map {st['map_id']} ({st['x']},{st['y']})")

            a = unwrap(await s.call_tool(
                "bot_act", {"action": "move_to", "x": st["x"] + 50, "y": st["y"]}))
            print("PASS act(move_to):" if a["status"] == "success" else "note act(move_to):", a)

            b = unwrap(await s.call_tool(
                "bot_act", {"action": "idle", "chat_message": "測試中 abc", "emote": "F2"}))
            print("act(say+emote+idle):", b)

            w = unwrap(await s.call_tool("bot_wait", {"timeout_s": 5}))
            print("PASS wait:", w["wake_reason"])

            blocked = unwrap(await s.call_tool("bot_act", {"action": "idle", "chat_message": "@gm hi"}))
            assert blocked["status"] == "failed" and "blocked_prefix" in blocked["reason"]
            print("PASS chat filter blocks @-prefix")

    print("SMOKE OK")


asyncio.run(main())