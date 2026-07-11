# Bot Ecosystem — Architecture

Living document. Any change to a component, connection, or message type in the
bot system MUST update this file in the same commit. Diagrams render natively
on GitHub (Mermaid).

Status: Phase 1 done, Phase 2 (bot-mcp) **not started** — tracking in
[issue #3](https://github.com/ckw1206/MapleStory-v113-Server-Eimulator/issues/3).

## Component map (as built today)

```mermaid
flowchart TB
    subgraph SIDECAR["bot-sidecar (Python, interim LLM driver)"]
        BRAIN["Brain<br/>(OpenAI-compatible LLM,<br/>e.g. Ollama)"]
        REFLEX["ReflexLayer<br/>(auto-potion, no LLM)"]
        SWSC["WebSocketClient<br/>(spawn on connect, reconnect)"]
        BRAIN --> SWSC
        REFLEX --> SWSC
    end

    subgraph SERVER["Java game server (docker: e113-server)"]
        BWS["BotServer<br/>(Netty WS :9999, token auth)"]
        BSESS["BotSession<br/>(action dispatch, single-bot guard,<br/>1 Hz snapshots, damaged/died events)"]
        HANDLERS["handlers:<br/>movement / combat / loot / chat"]
        TOUCH["TouchDamageSimulator<br/>(500 ms proximity, PADamage,<br/>only when a real player is on the map)"]
        PERC["PerceptionBuilder"]
        WORLD["Game world<br/>(MapleMap, mobs, drops, players)"]
        LOGIN["Login/Channel servers<br/>(:8484 / :8585–8604)"]
        BWS --> BSESS --> HANDLERS --> WORLD
        BSESS --> PERC --> WORLD
        TOUCH --> WORLD
        LOGIN --> WORLD
    end

    DB[("MySQL<br/>(docker: e113-mysql)")]
    PLAYERS["Real players<br/>(TMS v113 game clients)"]

    SIDECAR <-- "WebSocket + JSON<br/>ws://127.0.0.1:9999/ws?token=…" --> BWS
    PLAYERS <-- "v113 game protocol<br/>login :8484, channels :8585–8604" --> LOGIN
    SERVER <--> DB
```

The bot character has **no game client**: it is loaded straight from the DB
(`tms.BotCharacterId` in `Settings.ini`) behind a mock network session, and is
driven entirely over the WebSocket. Real players connect with the normal TMS
v113 client and see the bot as just another character on the map.

## Connections

| Link | Transport | Auth | Config |
|---|---|---|---|
| bot-sidecar → server | WebSocket, JSON text frames | `?token=` = `tms.BotToken` | `bot-sidecar/config.yaml` |
| players → server | v113 game protocol | game accounts | ports 8484, 8585–8604 |
| server → MySQL | JDBC | `Settings.ini` (`mysql:3306` inside docker) | `.env` |
| bot-sidecar → LLM | OpenAI-compatible HTTP | `api_key` | `bot-sidecar/config.yaml` |

## Wire protocol (bot ⇄ BotServer)

Inbound to server, one JSON object per text frame:
`{"action": name, "seq": ≥1, "args": {…}}` —
`spawn{mapId}`, `idle`, `move_to{x,y}`, `face{expressionId}`, `attack{mobId:oid}`,
`pickup{dropId:oid}`, `use_item{itemId}`, `say{text}`.

Outbound from server:

- `action_done{seq, action}` / `action_failed{seq, reason}` (seq 0 = unparseable request)
- `snapshot{data}` at 1 Hz — `mapId, position{x,y}, hp, maxHp, mp, maxMp, level, inventorySummary, mobs, drops, players, portals`
- `event{event, data}` — `damaged{damage, mobId, hp, maxHp}`, `died{}`

## Planned: Phase 2+ — bot-mcp (issue #3, not built yet)

The sidecar's built-in brain will be replaced by an agent harness talking MCP
to a thin `bot-mcp` middleware; plan in
`docs/superpowers/plans/2026-07-11-bot-mcp-phase2.md`.

```mermaid
flowchart TB
    HARNESS["Agent harness<br/>(Claude Code / Hermes / Codex —<br/>memory, skills, persona)"]
    BOTMCP["bot-mcp (Python)<br/>3 MCP tools: bot_perceive / bot_act / bot_wait<br/>+ state cache, event ring, reflex, Big5 chat filter"]
    SERVER2["Java game server<br/>(BotServer WS :9999 — unchanged protocol)"]

    HARNESS <-- "MCP over stdio<br/>(python -m botmcp)" --> BOTMCP
    BOTMCP <-- "WebSocket ws://127.0.0.1:9999/ws?token=…" --> SERVER2
```

Java deltas still needed for Phase 2: player-chat event forwarding
(`chat` event), `mob_killed` event, presence gating on actions
(`no_player_on_map`), snapshot `name`/`job`/`mesos`, server-side `^[@!/]`
chat reject.
