package server.bot;

import server.bot.json.JsonObject;

public interface BotActionHandler {
    boolean handle(BotSession session, BotCharacter bot, String actionName, JsonObject args);
    String getCapabilityName();
}