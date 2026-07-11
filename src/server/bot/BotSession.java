package server.bot;

import io.netty.channel.Channel;
import io.netty.handler.codec.http.websocketx.TextWebSocketFrame;
import server.ServerProperties;
import server.bot.handlers.ChatHandler;
import server.bot.handlers.CombatHandler;
import server.bot.handlers.LootHandler;
import server.bot.handlers.MovementHandler;
import server.bot.json.JsonObject;
import server.bot.json.JsonParser;
import server.bot.json.JsonValue;

import java.util.HashMap;
import java.util.Map;

public class BotSession {

    private final Channel ctx;
    private final String channelId;
    private BotCharacter bot;
    private final Map<String, BotActionHandler> capabilities;

    public BotSession(Channel ctx) {
        this.ctx = ctx;
        this.channelId = ctx.id().asLongText();
        this.capabilities = new HashMap<>();
        capabilities.put("movement", new MovementHandler());
        capabilities.put("combat",   new CombatHandler());
        capabilities.put("loot",     new LootHandler());
        capabilities.put("chat",     new ChatHandler());
    }

    public String getChannelId() { return channelId; }
    public BotCharacter getBot() { return bot; }

    public void onMessage(String text) {
        JsonObject action;
        try {
            action = (JsonObject) JsonParser.parse(text);
        } catch (Exception e) {
            // seq 0 is reserved for replies where the request seq could not be parsed;
            // clients must use seq >= 1
            sendActionFailed(0, "malformed_json");
            return;
        }

        String name = action.getString("action");
        if (name == null) {
            sendActionFailed(action.getInt("seq", 0), "missing_action");
            return;
        }
        int seq = action.getInt("seq", 0);
        JsonObject args = action.getJsonObject("args");

        // spawn is session lifecycle — handled directly here
        if ("spawn".equals(name)) {
            if (args == null) {
                sendActionFailed(seq, "missing_args");
                return;
            }
            int mapId = args.getInt("mapId", -1);
            if (mapId == -1) {
                sendActionFailed(seq, "missing_mapId");
                return;
            }
            if (bot == null) {
                try {
                    int charId = ServerProperties.getBotCharacterId();
                    bot = new BotCharacter(charId);
                    if (!bot.isLoaded()) {
                        bot = null;
                        sendActionFailed(seq, "char_load_failed");
                        return;
                    }
                } catch (Exception e) {
                    e.printStackTrace();
                    bot = null;
                    sendActionFailed(seq, "char_load_failed");
                    return;
                }
            }
            try {
                if (!bot.spawn(mapId)) {
                    sendActionFailed(seq, "bad_mapId");
                    return;
                }
                BotServer.getInstance().startSnapshotBroadcaster(this);
                sendActionDone(seq, "spawn");
            } catch (Exception e) {
                sendActionFailed(seq, "error: " + e);
            }
            return;
        }

        if (bot == null || bot.getMap() == null) {
            sendActionFailed(seq, "not_spawned");
            return;
        }

        // Idle is always allowed
        if ("idle".equals(name)) {
            sendActionDone(seq, "idle");
            return;
        }

        // Dispatch to capability handlers
        String capKey = null;
        if ("move_to".equals(name) || "face".equals(name)) capKey = "movement";
        else if ("attack".equals(name)) capKey = "combat";
        else if ("pickup".equals(name) || "use_item".equals(name)) capKey = "loot";
        else if ("say".equals(name)) capKey = "chat";

        if (capKey == null) {
            sendActionFailed(seq, "unknown_action: " + name);
            return;
        }
        if (args == null) {
            sendActionFailed(seq, "missing_args");
            return;
        }

        BotActionHandler h = capabilities.get(capKey);
        try {
            boolean ok = h.handle(this, bot, name, args);
            if (ok) {
                sendActionDone(seq, name);
            } else {
                sendActionFailed(seq, name);
            }
        } catch (Exception e) {
            sendActionFailed(seq, "error: " + e);
        }
    }

    public void onDisconnect() {
        if (bot != null) {
            bot.despawn();
            bot = null;
        }
    }

    // --- outbound helpers ---

    public void sendSnapshot(JsonValue snapshotData) {
        JsonObject msg = new JsonObject();
        msg.put("type", "snapshot");
        msg.put("data", snapshotData);
        ctx.writeAndFlush(new TextWebSocketFrame(msg.toString()));
    }

    public void sendActionDone(int seq, String actionName) {
        JsonObject msg = new JsonObject();
        msg.put("type", "action_done");
        msg.put("seq", seq);
        msg.put("action", actionName);
        ctx.writeAndFlush(new TextWebSocketFrame(msg.toString()));
    }

    public void sendActionFailed(int seq, String reason) {
        JsonObject msg = new JsonObject();
        msg.put("type", "action_failed");
        msg.put("seq", seq);
        msg.put("reason", reason);
        ctx.writeAndFlush(new TextWebSocketFrame(msg.toString()));
    }

    void close() {
        ctx.close();
    }
}
