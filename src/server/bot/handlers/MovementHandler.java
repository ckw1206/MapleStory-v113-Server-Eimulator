package server.bot.handlers;

import server.bot.BotActionHandler;
import server.bot.BotCharacter;
import server.bot.BotSession;
import server.bot.json.JsonObject;
import tools.MaplePacketCreator;

public class MovementHandler implements BotActionHandler {

    @Override
    public boolean handle(BotSession session, BotCharacter bot, String actionName, JsonObject args) {
        if ("move_to".equals(actionName)) {
            int x = args.getInt("x", 0);
            int y = args.getInt("y", 0);
            bot.moveTo(x, y);
            return true;
        } else if ("face".equals(actionName)) {
            int expressionId = args.getInt("expressionId", 0);
            bot.getCharacter().getMap().broadcastMessage(
                    MaplePacketCreator.facialExpression(bot.getCharacter(), expressionId));
            return true;
        }
        return false;
    }

    @Override
    public String getCapabilityName() { return "movement"; }
}