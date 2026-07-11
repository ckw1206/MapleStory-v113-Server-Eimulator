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

1. Set `tms.BotToken` and `tms.BotCharacterId` in `Settings.ini` (the bot character
   must exist in the DB — minimal seed SQL is in the header of `bot-smoke-test.mjs`).
2. Smoke-test the WS API (node ≥ 22, no deps):

   ```sh
   BOT_TOKEN=<tms.BotToken> node bot-smoke-test.mjs
   ```

3. Run the sidecar (Python ≥ 3.10, plus an OpenAI-compatible LLM endpoint such as
   Ollama):

   ```sh
   cd bot-sidecar
   pip install -r requirements.txt
   # edit config.yaml: ws_url token, model endpoint, spawn map
   python main.py
   ```

`docker compose down -v` wipes the DB volume — the bot character (and all
accounts) must be re-seeded afterwards.
