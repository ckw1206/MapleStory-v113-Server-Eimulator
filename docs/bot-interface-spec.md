# Bot Control Interface — Full Spec

Exhaustive reference for every interface the bot system exposes: the Java WS
server's wire protocol, and the two independent front-ends that drive it
(`bot-sidecar/`, `bot-mcp/`). Companion to [`bot-ecosystem.md`](bot-ecosystem.md)
(architecture diagrams, living doc) — this file is the field-by-field detail
and the current known-bugs list, written to support a review of why the bot
"isn't working" as of 2026-07-12.

**Read this first:** bot-sidecar and bot-mcp are **not** layered — they are
two alternate, mutually-exclusive front-ends to the same single Java bot
character. Only one can hold a spawned session at a time (§1.4). Running both
against the same server is a guaranteed conflict, not a supported topology.

---

## 1. Java WS server (`src/server/bot/`)

### 1.1 Transport & auth

- Netty WebSocket server, fixed path `/ws`, port from `tms.BotPort`
  (`ServerProperties.java`, default `9999`).
- Binds all interfaces (comment in `BotServer.java`: "binds all interfaces
  because docker port-mapping needs it; token auth is the boundary") — **no
  IP allowlisting, token is the only access control.**
- Auth: query-string param `token=` on the WS upgrade request
  (`ws://host:port/ws?token=...`), compared against `tms.BotToken`. No header
  auth exists. Mismatch or **missing/blank `tms.BotToken`** → the connection
  is rejected with a raw HTTP 401 before the WS handshake completes (fails
  closed — if the token isn't configured, nothing can ever connect).
- Max frame size 65536 bytes both for the HTTP aggregator and the WS
  handler. Only `TextWebSocketFrame` is handled; any other frame type is
  silently ignored (no error, no log).

### 1.2 Message envelope

Inbound (client → server):
```json
{"action": "<string>", "seq": <int>, "args": {"...": "..."}}
```
- `action` — required. Missing/null → `action_failed` reason `missing_action`.
- `seq` — optional, defaults to `0`. Convention only ("clients must use seq
  ≥ 1") — **not enforced**; sending `seq: 0` is never rejected.
- `args` — required object for every action except `spawn` (checked
  separately) and `idle` (not needed at all).
- Malformed JSON → `{"type":"action_failed","seq":0,"reason":"malformed_json"}`.

Outbound (server → client), by `type`:

| type | shape | trigger |
|---|---|---|
| `action_done` | `{seq, action}` | action succeeded |
| `action_failed` | `{seq, reason}` | action failed / malformed input |
| `snapshot` | `{data: {...full perception object...}}` | every 1000 ms per spawned session (fixed, not configurable) |
| `event` | `{data: {event: "<name>", ...extra fields flattened in}}` | see §1.6 |

### 1.3 Action catalog

| action | args | capability handler | requires real player on map? | notes |
|---|---|---|---|---|
| `spawn` | `mapId` (int) | inline in `BotSession` | no | claims the global singleton lock (§1.4); always enters at map portal 0; auto-heals to full HP if HP ≤ 0 |
| `idle` | none | inline | **no — explicitly bypassed** | always succeeds once spawned |
| `move_to` | `x`, `y` (int) | movement | yes | **teleport**, zero validation — no foothold/collision/bounds check, no pathing |
| `face` | `expressionId` (int, default 0) | movement | yes | broadcasts a facial-expression packet; no range validation on the id |
| `attack` | `mobId` (int — **this is the mob's map object id / `oid`, not its template id**) | combat | yes | explicit code comment: "test-harness capability, not a simulated legit player: no range/aggro/skill checks" — no distance limit, no cooldown |
| `pickup` | `dropId` (int, object id) | loot | yes | lock-protected against concurrent pickup; respects drop ownership (`getOwner()`) |
| `use_item` | `itemId` (int) | loot | yes | only items in the `USE` inventory category (leading digit of the item id) are usable; requires the bot to actually hold ≥1 |
| `say` | `text` (string) | chat | yes | 70-byte **Big5** cap (not UTF-8, not char count), truncated char-by-char; rejects text starting with `@`, `!`, `/` |

**Field-name trap:** `attack`'s request field `mobId` is the object id
(`oid`), but the `mob_killed` *event*'s own `mobId` field is the monster
template id. Same field name, opposite meaning between request and event —
a client that reuses a snapshot's `mobs[].id` (template id) as the `attack`
arg will silently fail to find the mob.

**Generic failure reason collapse:** on a capability-handler failure, the
reported `reason` is just the action name itself (e.g.
`{"reason":"attack"}`) — there is no way to distinguish "mob not found" from
"mob already dead" from "wrong item type" from the reason string alone. All
four dispatched-capability actions (`move_to`/`face`/`attack`/`pickup`/`use_item`/`say`)
share this limitation.

### 1.4 Gating & single-bot lock

- `BotSession.BOT_IN_USE` is a **static, process-wide** `AtomicBoolean`.
  Only one WS session, server-wide, may hold a spawned bot at a time.
  `spawn` while another session holds it → `action_failed reason: bot_in_use`,
  with no retry from either Python front-end.
- The bot character itself is also singular: `tms.BotCharacterId` (default
  `1`) — every session that does spawn loads the exact same DB character.
- Every action except `spawn`/`idle` requires
  `BotServer.hasRealPlayer(map, botId)` — at least one non-clone, non-hidden
  character other than the bot on the bot's current map. Otherwise:
  `action_failed reason: no_player_on_map`. **This means the bot can only
  `idle` whenever no real player shares its map** — the most common
  "nothing happens" symptom when testing solo.
- Bot always spawns on **channel 1** (hardcoded in `BotCharacter`'s
  constructor) regardless of server channel config.

### 1.5 Perception snapshot (`PerceptionBuilder`, 1 Hz)

```json
{
  "mapId": 0, "position": {"x":0,"y":0},
  "hp":0,"maxHp":0,"mp":0,"maxMp":0,"level":0,"name":"","job":0,"mesos":0,
  "inventorySummary": [{"type":"EQUIP|USE|SETUP|ETC|CASH","id":0,"qty":0}],
  "mobs":   [{"id": 0, "oid": 0, "x":0, "y":0, "hpPct": 0}],
  "drops":  [{"oid": 0, "itemId": 0, "x":0, "y":0}],
  "players":[{"id": 0, "name": "", "x":0, "y":0}],
  "portals":[{"name": "", "x":0, "y":0}]
}
```
- `mobs`/`drops`: queried within 1500px of the bot, capped at 64 entries
  each, dead mobs and picked-up drops filtered out. `hpPct` is truncated
  (not rounded) integer division.
- `players`: no range limit (whole map), capped at 64, filters clones/hidden/self.
- `drops` has **no ownership filtering** at the perception layer — a drop
  reserved for another player still shows up; only the `pickup` handler
  enforces ownership.
- `inventorySummary` has no cap — every item in every inventory tab, every
  tick.

### 1.6 Events

| event | fields | trigger |
|---|---|---|
| `chat` | `senderId`, `senderName`, `text` | a **real player** (not the bot) speaks on the bot's map — fans out to every bot session on that map |
| `mob_killed` | `oid` (the killed mob's object id), `mobId` (its **template id**) | bot's `attack` reduces a mob's HP to 0 |
| `damaged` | `damage`, `mobId` (template id), `hp`, `maxHp` | touch-damage tick hits the bot (see §1.7) |
| `died` | *(no fields)* | bot HP reaches ≤0 from touch damage |

The bot's own `say` does **not** produce a `chat` event — only other real
players' chat is relayed back as an event.

### 1.7 Touch-damage simulator

Since the bot has no real client to receive normal monster-AI touch-damage
packets, `TouchDamageSimulator` fakes it: a 500ms-tick `Runnable`, only
active while a real player shares the map, querying mobs within 50px
(melee-range, much tighter than the 1500px perception radius). Each mob can
touch-damage the bot at most once per 1000ms (per-mob cooldown); damage
comes from the mob's real `PADamage` WZ field (`MobPADamage.java`), with a
silent `level*5+10` fallback if the WZ lookup fails for any reason
(exceptions there are swallowed with no log).

**Death does not despawn the bot.** Once HP reaches 0, `died` fires exactly
once and the simulator just skips future ticks — the character stays on the
map, snapshots keep broadcasting `hp: 0` forever, until a client-issued
`spawn` (which despawns + heals to full) or a disconnect. There is no
server-side auto-respawn.

### 1.8 There is no server-side reflex/auto-potion logic

Confirmed by a repo-wide search — the only automatic HP-related behavior on
the Java side is the heal-to-full-on-`spawn()`. All decision-making (when to
move/attack/heal/flee) is entirely the client's responsibility; the server
is a pure command executor + passive perception feed.

---

## 2. `bot-sidecar/` — standalone LLM agent

Single Python process: connects, perceives, decides (reflex + LLM), and
acts — no external driver.

### 2.1 Connection (`websocket_client.py`)

- Synchronous `websocket-client` (`create_connection`), 10s connect timeout,
  background reader thread pushing parsed JSON onto a queue.
- **No request/reply correlation at the transport layer** — `seq`
  bookkeeping is entirely `main.py`'s job (`in_flight` dict), fire-and-forget.
- Reconnect: capped at **5 attempts**, exponential 1s→30s backoff, then
  `exit(1)` — the whole process hard-exits with no supervisor signal beyond
  the exit code.

### 2.2 Main loop (`main.py`)

Connects once, sends `spawn` immediately, then loops on `ws.recv(timeout=1.0)`:

- `snapshot` → cache as `current_state`, run the reflex layer every tick,
  run the LLM brain only every `brain_interval_seconds` (default 5s).
- `event` → always fed to the brain's memory; on `died`, resets local
  reflex/brain state — **but never re-sends `spawn`** (see §4, root-cause #1).
- `action_done`/`action_failed` → pop the matching `in_flight` entry; for
  `pickup`, always releases the reflex's in-flight lock on the drop
  regardless of outcome.

Outbound action shape: `{"action": ..., "args": {...}, "seq": ...}`.

### 2.3 Reflex layer (`reflex_layer.py`)

- HP-crisis threshold: **hardcoded `0.30`** (not configurable — no YAML/env
  key exists for it, unlike bot-mcp's `hp_threshold`).
- Fires `use_item` whenever `hp/maxHp < 0.30` **and** a matching potion
  exists in `inventorySummary` — **no `hp <= 0` guard**, so it will keep
  trying to "heal" a dead (0 HP) character.
- **No cooldown/backoff at all** — re-fires every ~1s tick the condition
  holds, throttled only by the server's 1Hz snapshot cadence.
- Auto-loot: picks the first not-already-in-flight drop each tick (mutually
  exclusive with the potion reflex per tick — potion checked first).

### 2.4 LLM brain (`brain.py`, `intent_schema.py`, `persona.py`)

- OpenAI-compatible chat-completions client (`openai.OpenAI(base_url=...)`),
  **not** Anthropic — points at a local/self-hosted endpoint
  (`config.yaml`: `http://127.0.0.1:8000/v1`, model `MiniMax-M2.7`).
- Tool schema `bot_action`: `action` enum
  `{move_to, attack, pickup, use_item, say, face, idle}`, `args` is an
  unvalidated free-form object (server-side handlers are the real validators).
- One retry on schema-validation failure; **any other exception (network,
  auth, malformed response) is swallowed silently with no log at all** —
  the brain just stops acting with zero console signal.
- System prompt is persona-templated (`{name}`, `{greeting}` from config).
- Per-event memory formatting: only `chat` events get a custom
  "Event: chat from {senderName}: {text}" format; every other event
  (`damaged`, `mob_killed`, `died`) falls back to a generic
  `Event: {name} ({extra})` string.

### 2.5 `scripted_stub.py`

A separate, standalone smoke-test script (not part of the normal run path,
no LLM/reflex imports): spawn → wait for one snapshot → fire one
`move_to`/`attack`/`pickup`/`say` unconditionally, print replies, exit.

### 2.6 Config (`config.py`, `config.yaml`)

Loaded from a **hardcoded relative path** `"config.yaml"` — must be launched
with CWD = `bot-sidecar/`. Each field is YAML value overridable by a
`BOT_*` env var; see the consolidated table in §5.

---

## 3. `bot-mcp/` — MCP middleware

Exposes bot control as 3 MCP tools for an **external** agent host (e.g. a
Claude/agent harness over stdio) to drive. Makes no LLM calls itself — the
decision-making lives entirely outside this process.

### 3.1 MCP tool surface (`server.py`, `FastMCP`, server name `maplestory-bot`)

- **`bot_perceive()`** — no args. Returns the world-state payload (§3.4).
- **`bot_act(action, x=None, y=None, target_oid=None, item_id=None, chat_message=None, emote=None)`**
  — one game turn. `action ∈ {idle, move_to, attack, pickup, use_item}`.
  Order of sub-actions: `say → emote → action`. `chat_message` (~70 bytes,
  filtered client-side first) and `emote` (`F1`–`F7`) are optional add-ons
  applied before the main action. Returns
  `{status: "success"|"partial"|"failed", parts: {name: result}, reason}` —
  `"partial"` means some of the say/emote/action sub-steps succeeded and
  others didn't.
- **`bot_wait(timeout_s=30)`** — blocks (clamped to `[1, 120]` regardless of
  input) until a *notable* event (`chat`, `damaged`, `died`, `mob_killed`) or
  timeout, then returns a fresh perceive payload plus `wake_reason`.

### 3.2 `bot_perceive`/`bot_wait` payload shape

```json
{
  "bot_status": {"name":"","job":"beginner|warrior|magician|bowman|thief|pirate|gm",
                 "level":0,"hp":0,"max_hp":0,"mp":0,"max_mp":0,
                 "mesos":0,"map_id":0,"x":0,"y":0},
  "nearby_entities": {
    "players": [...],
    "monsters": [{"oid":0,"mob_id":0,"x":0,"y":0,"hp_pct":0}],
    "drops":    [{"oid":0,"item_id":0,"x":0,"y":0}],
    "portals":  [...]
  },
  "chat_history": [{"ts":"HH:MM:SS","sender":"","message":""}],
  "pending_events": ["<event>: <data>", "..."]
}
```
`job_name()` mislabels any job-id range 600–899 as `"beginner"` (those
ranges aren't in the enumerated buckets) — a silent misclassification for
job families outside the originally-covered five. `pending_events` is
**consumed exactly once**: a second `bot_perceive` call right after returns
an empty list (drain semantics on the internal event ring).

### 3.3 Connection (`ws_client.py`)

- `websocket.WebSocketApp` (event-driven), URL built as
  `f"{ws_url}?token={token}"`.
- **Auto-spawn on connect** — `_on_open` immediately fires `spawn`. **No
  retry on spawn failure** — if it comes back `bot_in_use` (the global lock
  held by the other front-end), the client just sits connected with the
  state store permanently empty; every subsequent `bot_perceive` silently
  returns an all-zero payload (`map_id: 0`, empty lists) with no explicit
  "not spawned" signal.
- Reconnect: **uncapped**, fixed 3s delay, no backoff growth — will retry
  forever, unlike bot-sidecar's capped exponential-backoff-then-exit.
- **On `died`, schedules an actual re-`spawn()` after a 3s delay** — this is
  the piece bot-sidecar is missing (§4).
- Request/reply correlation *is* implemented here (`send_action` blocks on a
  per-seq `threading.Event`, 10s default timeout) — a real difference from
  bot-sidecar's fire-and-forget model.

### 3.4 Reflex (`ws_client.py`, potion-only)

- `hp_threshold` **is** a real config key (default `0.40`), unlike
  bot-sidecar's hardcoded `0.30`.
- **Has an `hp <= 0` guard** — explicitly will not try to potion-heal a
  dead character (bot-sidecar's reflex has no such guard).
- Exponential backoff: `2.0 * 2^min(failures,4)` seconds → `2,4,8,16,32s`
  sequence, vs. bot-sidecar's no-cooldown-at-all reflex.

### 3.5 State store (`state.py`)

Single-condition-variable cache: last snapshot only (no history), chat ring
(maxlen 20), event ring (maxlen 64). `NOTABLE_EVENTS = {chat, damaged, died,
mob_killed}` are the only ones that wake `bot_wait`.

### 3.6 Chat filter (`chat_filter.py`)

Client-side pre-filter matching the Java server's own truncation logic:
70-byte Big5 cap (heuristic byte-slice truncation, can drop a trailing
character even if it would technically fit), rejects `@`/`!`/`/` prefixes
as a typed `ChatBlockedError` (vs. the Java side's silent `action_failed`).
Also round-trips **every** message through Big5 even under the cap, so any
character not representable in Big5 (most emoji, many symbols) is silently
mangled via `errors="replace"`, not just on truncation.

---

## 4. Known bugs / risk list — likely root causes of "bot not working"

Ranked by how likely each is to explain a stuck/inert bot, based on reading
the current code (some of this is from the uncommitted working-tree changes
to `bot-sidecar/main.py`, `brain.py`, `BotCharacter.java`):

1. **bot-sidecar never re-spawns after death.** `main.py`'s `died` handler
   only clears local state — it never re-sends `spawn`. Combined with the
   Java side never despawning a dead bot (§1.7), a bot-sidecar-driven bot
   that dies and runs out of potions is stuck at `hp:0` **permanently**,
   with no code path that recovers it. bot-mcp does not have this bug (its
   `ws_client.py` explicitly re-spawns 3s after `died`).
2. **The single static `BOT_IN_USE` lock** means bot-sidecar and bot-mcp (or
   two instances of either) can never run concurrently against one server.
   Whichever spawns second gets `bot_in_use` forever, and neither Python
   front-end retries a failed spawn on its own.
3. **Missing/blank `tms.BotToken` in `Settings.ini`** makes the Java
   handshake validator reject 100% of connections, regardless of what token
   either Python client sends. Worth checking first — both ship a
   placeholder `changeme` default that must match exactly.
4. **`Brain.think`'s silent broad `except Exception`** means an
   unreachable/misconfigured LLM endpoint produces **zero console output**
   — the bot simply stops taking LLM-driven actions with no visible error,
   only reflex activity (if any) remains observable.
5. **No real player on the bot's map** — every action but `idle` fails with
   `no_player_on_map`. Easy to overlook when testing solo without a second
   character logged into the same map as the bot.
6. **`spawn_map_id` drift** across `config.yaml`/`config.yaml.example` for
   both front-ends (values `10000`, `50000`, `100000000` all appear across
   the four files) — worth confirming which map is actually intended before
   debugging further; a mismatch here means the "real player" being watched
   and the bot may not even be on the same map.
7. **`attack`'s `mobId` field-name trap** (§1.3) — a client using the
   snapshot's `mobs[].id` (template id) instead of `mobs[].oid` for the
   `attack` arg will silently and permanently fail to hit anything.
8. Generic per-handler failure reasons (`reason` = action name) make several
   distinct failure modes indistinguishable from the wire alone — useful to
   know when reading logs, not fixable without a server-side change.

---

## 5. Consolidated config reference

| Value | bot-sidecar | bot-mcp | Java (`Settings.ini`) |
|---|---|---|---|
| WS host:port | `config.yaml: ws_url` (env `BOT_WS_URL`), default `127.0.0.1:9999` | `config.yaml: ws_url`, no env override, default `127.0.0.1:9999` | `tms.BotPort` (default `9999`) |
| Auth token | embedded in `ws_url` query string | separate `token` key, appended as `?token=` | `tms.BotToken` (no default — unset ⇒ always rejects) |
| Bot character | n/a (server picks it) | n/a (server picks it) | `tms.BotCharacterId` (default `1`) |
| Spawn map | example `10000` / local `50000` / code fallback `100000000` | example `100000000` / local `10000` | n/a — bot supplies `mapId` |
| Potion item id | `2000002` (env `BOT_POTION_ITEM_ID`) | `2000002` | n/a |
| HP reflex threshold | `0.30`, hardcoded, **not configurable** | `hp_threshold: 0.40`, real config key | n/a |
| LLM base URL / key / model | `http://127.0.0.1:8000/v1` / `not-needed` / `MiniMax-M2.7` (all env-overridable) | n/a — no LLM in bot-mcp | n/a |
| Brain interval | `5`s (env `BOT_BRAIN_INTERVAL_SECONDS`) | n/a | snapshot fixed at 1000ms server-side |
| Reconnect policy | 5 attempts, 1→30s backoff, then hard `exit(1)` | uncapped, fixed 3s delay | n/a |
| Chat byte cap | n/a (no client-side filter) | `70` bytes, Big5 | `70` bytes, Big5 (server-side truncation is the real backstop either way) |

---

## 6. File index

| File | Role |
|---|---|
| `src/server/bot/BotServer.java` | Netty WS bootstrap, auth, session registry, snapshot/touch-damage schedulers, cross-session chat relay |
| `src/server/bot/BotSession.java` | Per-connection dispatch loop, action routing, single-bot lock |
| `src/server/bot/BotActionHandler.java` | Capability handler interface |
| `src/server/bot/handlers/{Movement,Combat,Loot,Chat}Handler.java` | Per-capability action logic |
| `src/server/bot/PerceptionBuilder.java` | Snapshot payload construction |
| `src/server/bot/BotCharacter.java` | Wraps a real `MapleCharacter` as the bot; spawn/despawn/moveTo/damage |
| `src/server/bot/TouchDamageSimulator.java` | Faked contact-damage tick (no real client to receive it otherwise) |
| `src/server/bot/MobPADamage.java` | Direct WZ read for touch-damage amounts |
| `src/server/bot/json/*` | Hand-rolled minimal JSON parser/serializer used by the WS protocol |
| `bot-sidecar/main.py` | Standalone agent entrypoint/loop |
| `bot-sidecar/websocket_client.py` | Sync WS transport, no request/reply correlation |
| `bot-sidecar/brain.py`, `intent_schema.py`, `persona.py` | LLM decision loop, tool schema, prompt construction |
| `bot-sidecar/reflex_layer.py` | Low-latency potion/loot reflex |
| `bot-sidecar/scripted_stub.py` | Standalone no-LLM smoke test |
| `bot-mcp/botmcp/server.py` | MCP tool surface (`bot_perceive`/`bot_act`/`bot_wait`) |
| `bot-mcp/botmcp/ws_client.py` | Event-driven WS transport, auto-spawn/reconnect/respawn, seq correlation, potion reflex |
| `bot-mcp/botmcp/state.py` | Cached snapshot/chat/event store with wait/notify |
| `bot-mcp/botmcp/chat_filter.py` | Client-side chat pre-filter |
