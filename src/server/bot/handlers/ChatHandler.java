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
        if (text.isEmpty()) return false;
        char c0 = text.charAt(0);
        if (c0 == '@' || c0 == '!' || c0 == '/') return false;
        int byteCap = 70;
        java.nio.charset.Charset big5 = java.nio.charset.Charset.forName("Big5");
        byte[] encoded = text.getBytes(big5);
        if (encoded.length > byteCap) {
            int acc = 0;
            int cut = 0;
            for (int i = 0; i < text.length(); i++) {
                int charBytes = String.valueOf(text.charAt(i)).getBytes(big5).length;
                if (acc + charBytes > byteCap) break;
                acc += charBytes;
                cut = i + 1;
            }
            text = text.substring(0, cut);
        }
        bot.getCharacter().getMap().broadcastMessage(
                MaplePacketCreator.getChatText(bot.getId(), text, false, 0),
                bot.getPosition());
        return true;
    }
}
