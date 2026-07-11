// Bot API smoke test: auth boundary + spawn/action round-trip against ws://localhost:9999/ws
// Usage: BOT_TOKEN=<tms.BotToken> node bot-smoke-test.mjs   (node >= 22, no deps)
// Needs a running server and an existing character at tms.BotCharacterId. On a fresh DB,
// seed minimal rows first (defaults are fine for the rest):
//   INSERT INTO characters (id, accountid, name) VALUES (1, 1, 'LLMBot');
//   INSERT INTO inventoryslot (characterid, equip, `use`, setup, etc, cash) VALUES (1,24,24,24,24,24);
//   INSERT INTO mountdata (characterid) VALUES (1);
//   (plus an accounts row with id 1)
const TOKEN = process.env.BOT_TOKEN ?? "changeme";
const URL = "ws://localhost:9999/ws";

const results = [];
function log(name, ok, detail) {
  results.push(ok);
  console.log(`${ok ? "PASS" : "FAIL"}  ${name}${detail ? " — " + detail : ""}`);
}

function tryConnect(url, timeoutMs = 5000) {
  return new Promise((resolve) => {
    const ws = new WebSocket(url);
    const t = setTimeout(() => { ws.close(); resolve({ opened: false, reason: "timeout" }); }, timeoutMs);
    ws.onopen = () => { clearTimeout(t); resolve({ opened: true, ws }); };
    ws.onerror = () => {};
    ws.onclose = (e) => { clearTimeout(t); resolve({ opened: false, reason: `closed code=${e.code}` }); };
  });
}

// 1. no token → handshake must fail
{
  const r = await tryConnect(URL);
  log("connect without token rejected", !r.opened, r.opened ? "connection OPENED (auth bypass!)" : r.reason);
  if (r.opened) r.ws.close();
}

// 2. wrong token → handshake must fail
{
  const r = await tryConnect(URL + "?token=wrongtoken");
  log("connect with wrong token rejected", !r.opened, r.opened ? "connection OPENED (auth bypass!)" : r.reason);
  if (r.opened) r.ws.close();
}

// 3. correct token → connect, spawn, expect action_done + snapshot, then say
{
  const r = await tryConnect(`${URL}?token=${encodeURIComponent(TOKEN)}`);
  log("connect with correct token accepted", r.opened, r.opened ? "" : r.reason);
  if (r.opened) {
    const ws = r.ws;
    const inbox = [];
    const waiters = [];
    ws.onmessage = (e) => {
      const m = JSON.parse(e.data);
      inbox.push(m);
      for (let i = waiters.length - 1; i >= 0; i--) {
        if (waiters[i].pred(m)) { const w = waiters.splice(i, 1)[0]; clearTimeout(w.t); w.resolve(m); }
      }
    };
    const waitFor = (pred, ms, label) => new Promise((resolve) => {
      const hit = inbox.find(pred);
      if (hit) return resolve(hit);
      const t = setTimeout(() => resolve(null), ms);
      waiters.push({ pred, resolve, t });
    });

    ws.send(JSON.stringify({ action: "spawn", seq: 1, args: { mapId: 100000000 } }));
    const spawnReply = await waitFor((m) => m.seq === 1, 10000);
    log("spawn round-trip", spawnReply?.type === "action_done",
        spawnReply ? JSON.stringify(spawnReply) : "no reply in 10s");

    if (spawnReply?.type === "action_done") {
      const snap = await waitFor((m) => m.type === "snapshot", 5000);
      log("perception snapshot received", !!snap,
          snap ? `mobs=${snap.data?.mobs?.length} players=${snap.data?.players?.length} map=${snap.data?.mapId ?? "?"}` : "none in 5s");

      ws.send(JSON.stringify({ action: "say", seq: 2, args: { text: "pr2 verification" } }));
      const sayReply = await waitFor((m) => m.seq === 2, 5000);
      log("say action round-trip", sayReply?.type === "action_done",
          sayReply ? JSON.stringify(sayReply) : "no reply in 5s");

      ws.send(JSON.stringify({ action: "bogus_action", seq: 3, args: {} }));
      const bogus = await waitFor((m) => m.seq === 3, 5000);
      log("unknown action fails cleanly", bogus?.type === "action_failed",
          bogus ? JSON.stringify(bogus) : "no reply in 5s");
    }

    // malformed JSON → action_failed with reserved seq 0
    ws.send('{"action":');
    const mal = await waitFor((m) => m.seq === 0, 5000);
    log("malformed JSON -> action_failed seq 0", mal?.type === "action_failed" && mal?.reason === "malformed_json",
        mal ? JSON.stringify(mal) : "no reply in 5s");

    ws.close();
  }
}

console.log(results.every(Boolean) ? "ALL PASS" : "SOME FAILED");
process.exit(results.every(Boolean) ? 0 : 1);
