package server.bot.handlers;

import server.bot.BotActionHandler;
import server.bot.BotCharacter;
import server.bot.BotSession;
import server.bot.json.JsonObject;
import tools.MaplePacketCreator;

public class ChatHandler implements BotActionHandler {

    @Override
    public boolean handle(BotSession session, BotCharacter bot, String actionName, JsonObject args) {
        if (!"say".equals(actionName)) return false;
        String text = args.getString("text", "");
        bot.getCharacter().getMap().broadcastMessage(
                MaplePacketCreator.getChatText(bot.getId(), text, false, 0),
                bot.getPosition());
        return true;
    }
}
