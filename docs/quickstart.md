# Quick Start

## Run the server (Docker — recommended)

Runs MySQL and the game server together, no local JDK required.

```sh
make setup      # copy .env.example / Settings.ini.example if missing
make docker-up  # build the server image, start MySQL + the server
```

Edit `.env` and `Settings.ini` first if you need non-default credentials or world
settings. If the server is running in Docker, set `tms.Url` in `Settings.ini` to use
host `mysql` instead of `localhost` (see comment in `Settings.ini.example`) — it
reaches the MySQL container over the compose network rather than the published port.

Boot is ready when the logs show `Bot WS server listening` (`make docker-logs`).

Other targets: `make docker-down`, `make docker-logs`, `make docker-build` (rebuild
after code changes). Run `make help` for the full list, including the native
(non-Docker) `build`/`start`/`stop` flow.

### Requirements

- Docker + Docker Compose, **or** JDK 8–14 (all dependencies ship as jars in `dist/`)
  for the native flow. Not JDK 15+: the game scripts run on Nashorn, which was removed
  from the JDK in Java 15. The Docker image uses Java 11.

### Connect a game client

Use a TMS v113 client pointed at the server IP — login port `8484`, channel ports
`8585–8604`. Client text is Big5: on a non-Chinese Windows install, run the client
with the system ANSI codepage set to 950 (or via a locale emulator), otherwise
server text renders garbled.

## Run the LLM bot (optional)

Architecture overview: [bot-ecosystem.md](bot-ecosystem.md).

### Which character does the bot use?

The bot does **not** log in through a game client or account. The server loads the
character whose DB id is `tms.BotCharacterId` (Settings.ini) directly from MySQL and
places it on a map — no password, no login server. It appears to real players as a
normal character. Only **one** bot session can hold the character at a time; a second
connection gets `bot_in_use`. The character must exist in the DB (minimal seed SQL is
in the header of `bot-smoke-test.mjs`; note `docker compose down -v` wipes it).

### Server-side setup (once)

1. Set `tms.BotToken` (shared secret) and `tms.BotCharacterId` in `Settings.ini`,
   restart the server. The bot WS API listens on port `9999`.
2. Smoke-test the WS API (node ≥ 22, no deps):

   ```sh
   BOT_TOKEN=<tms.BotToken> node bot-smoke-test.mjs
   ```

### Drive the bot from an agent harness (Hermes / Claude Code) via MCP

`bot-mcp/` is an MCP **stdio** server: the harness launches `python -m botmcp` as a
child process and talks MCP over stdin/stdout. On startup bot-mcp opens the WebSocket
to the game server (`ws://…:9999/ws?token=…`), authenticates with the token, and
**auto-spawns** the bot character on `spawn_map_id` — the agent has no spawn/despawn
control. The server pushes a world snapshot every second plus events (player chat,
damaged, died, mob_killed); bot-mcp caches them and exposes exactly three tools:

- `bot_perceive()` — current status (name/job/level/hp/mesos/position), nearby
  players/monsters/drops/portals, last 20 chat lines, pending events.
- `bot_act(action, …)` — one game turn: `idle | move_to(x,y) | attack(target_oid) |
  pickup(target_oid) | use_item(item_id)`, plus optional `chat_message` (Big5,
  70-byte cap, `@ ! /` prefixes rejected) and `emote` (F1–F7).
- `bot_wait(timeout_s)` — block until something notable happens (or timeout), then
  return a fresh perceive payload with `wake_reason`.

A reflex layer inside bot-mcp auto-drinks a potion at ≤ 40% HP without involving the
agent. The server refuses all non-idle actions unless a **real player** is on the
bot's map (`no_player_on_map`), so test with a game client logged in on the same map.

Setup:

```sh
cd bot-mcp
pip install -r requirements.txt
cp config.yaml.example config.yaml   # set token (= tms.BotToken), spawn map, potion id
```

Then register it as a stdio MCP server in your harness, e.g. Claude Code:

```sh
claude mcp add maplestory-bot -e BOTMCP_CONFIG=<abs path>/bot-mcp/config.yaml -- python -m botmcp
```

For Hermes Agent (or any MCP-capable harness), add the equivalent stdio server entry
to its MCP config: command `python`, args `["-m", "botmcp"]`, working dir `bot-mcp/`
(or env `BOTMCP_CONFIG` pointing at the config file). The agent loop is then just:
`bot_wait` → read chat/events → `bot_act` (reply, move, fight) → repeat. The persona
/ play-loop skill is Phase 3.

### Legacy scripted sidecar (Phase 1, no MCP)

`bot-sidecar/` is the pre-MCP standalone loop (Python ≥ 3.10, plus an
OpenAI-compatible LLM endpoint such as Ollama):

   ```sh
   cd bot-sidecar
   pip install -r requirements.txt
   # edit config.yaml: ws_url token, model endpoint, spawn map
   python main.py
   ```

`docker compose down -v` wipes the DB volume — the bot character (and all
accounts) must be re-seeded afterwards.
