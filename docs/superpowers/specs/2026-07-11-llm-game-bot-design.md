# LLM Game Bot — Design Spec

Date: 2026-07-11
Status: approved design, pre-implementation
Reference inspiration: https://github.com/TinForge/MS-ML-Bot (vision-based; we do NOT use its approach — we own the server)

## Goal

An LLM-driven bot that plays on this v113 server like a real person: an autonomous
character other players can see, that grinds mobs and chats in-character. This is an
LLM-plays-game experiment — the agent loop (perceive → decide → act) is the deliverable.

Non-goals for v1 (module slots reserved, no code): quests, NPC dialog, shops,
map travel, parties, multiple simultaneous bots, MCP wrapper.

## Key constraint

LLM latency is 1–5 s; the game ticks at ~100 ms. Therefore the LLM never presses
buttons — it emits **intents**; deterministic code executes them.

## Architecture — 3 layers, 2 processes

```
┌─ Java server (this repo) ──────────────────────────────┐
│ Bot API module — new package src/server/bot/           │
│ • Spawns a real MapleCharacter (no client socket)      │
│   into a map; visible to other players                 │
│ • WebSocket endpoint (reuse bundled Netty 4.1.65),     │
│   localhost only, port from Settings.ini               │
│ • OUT: perception JSON — periodic snapshot + events    │
│ • IN: macro actions; server performs foothold pathing  │
│   and timing itself                                    │
└───────────────▲────────────────────────────────────────┘
                │ WebSocket, JSON messages
┌─ Python sidecar (new top-level dir bot-sidecar/) ──────┐
│ Reflex layer — no LLM: potion below HP threshold,      │
│   re-target, loot nearby                               │
│ LLM brain — on timer (~ every few sec) or on event     │
│   (player chat, HP crisis, area cleared):              │
│   state summary + persona + rolling memory → LLM →     │
│   validated intent → executor maps to macro actions    │
└────────────────────────────────────────────────────────┘
```

## Wire protocol (WebSocket, JSON)

Server → sidecar:
- `snapshot` (periodic, ~1/s): own state (map, pos, HP/MP, level, inventory summary),
  visible mobs (id, type, pos, HP%), drops, nearby players, portals/footholds summary.
- `event` (immediate): `chat` (speaker, text), `damaged`, `mob_killed`, `level_up`,
  `died`, `action_done` / `action_failed` (result of a macro action).

Sidecar → server:
- `{ "action": "<name>", "args": {...}, "seq": n }`
- v1 actions: `spawn`, `move_to(x, y)`, `attack(mobId)`, `pickup(dropId)`,
  `use_item(itemId)`, `say(text)`, `face(dir)`, `idle`.
- Server replies `action_done`/`action_failed(seq, reason)`.

Exact JSON field lists are defined at implementation time from what
`MapleCharacter`/`MapleMap` actually expose.

## Capability-module registry (extensibility requirement)

Both sides register capabilities by name; a capability = one Java action-handler class
+ one Python skill module. v1 ships `combat`, `loot`, `chat`, `movement`.
Future (`npc`, `shop`, `travel`, `party`, `quest`) = add one module per side; no protocol
change (`{action, args}` is generic). A failure in one module cannot break another:
Java handlers catch per-action, sidecar skills are isolated classes.

## LLM connection (sidecar)

- Single interface: **OpenAI-compatible chat completions**, via the `openai` Python
  package — the only LLM dependency.
- Config (YAML/env): `base_url`, `api_key`, `model`. Covers Ollama (`/v1`), OpenAI,
  Anthropic's OpenAI-compat endpoint, LM Studio, vLLM, OpenRouter.
- Intents are emitted via native tool-calling; the intent schema is sent as `tools`.
- Responses are validated against the intent schema; on failure, retry once with the
  validation error appended (makes 7B–14B local models usable).
- Prompt = system persona + compressed state text + rolling conversation/event memory
  (bounded window).

## Failure isolation

- Sidecar dies → bot idles; server despawns the character after a disconnect timeout.
- LLM call fails/hangs → reflex layer keeps character alive; brain retries with backoff.
- Server restarts → sidecar auto-reconnects and re-issues `spawn`.
- Malformed action JSON → server rejects with `action_failed`, never throws into game
  threads. All bot actions run through the same server code paths as real packet
  handlers, on the map's game thread.

## Security

WebSocket binds to localhost only; a shared token from Settings.ini is required on
connect. The bot API can create/control a character, so it must never be exposed
publicly.

## Testing

- Java: a scripted (non-LLM) sidecar stub exercises every macro action against a
  running server — spawn, walk, kill one mob, loot, say.
- Python: unit test for intent-schema validation/retry; brain loop testable with a
  mocked LLM client.
- End-to-end check: bot spawns in Henesys hunting ground, kills mobs, replies when a
  player talks to it.

## v1 deliverables

1. `src/server/bot/` — WS endpoint, bot character spawn, 8 macro actions, perception
   snapshots + events.
2. `bot-sidecar/` — Python: WS client, reflex layer, brain loop, OpenAI-compat client,
   config file, persona prompt.
3. The e2e grind+chat demo above.
