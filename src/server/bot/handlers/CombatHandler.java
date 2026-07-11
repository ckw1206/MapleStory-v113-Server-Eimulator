package server.bot.handlers;

import server.Randomizer;
import server.bot.BotActionHandler;
import server.bot.BotCharacter;
import server.bot.BotSession;
import server.bot.json.JsonObject;
import server.life.MapleMonster;
import server.maps.MapleMapObject;
import server.maps.MapleMapObjectType;

public class CombatHandler implements BotActionHandler {

    @Override
    public boolean handle(BotSession session, BotCharacter bot, String actionName, JsonObject args) {
        if (!"attack".equals(actionName)) return false;

        int mobOid = args.getInt("mobId", -1);
        if (mobOid == -1) return false;

        MapleMapObject mobObj = bot.getMap().getMapObject(mobOid, MapleMapObjectType.MONSTER);
        if (!(mobObj instanceof MapleMonster)) return false;
        MapleMonster mob = (MapleMonster) mobObj;

        if (!mob.isAlive()) return false;

        // Test-harness capability, not a simulated legit player: no range/aggro/skill checks
        float maxBase = bot.getCharacter().getStat().getCurrentMaxBaseDamage();
        int damage = Math.max(1, (int) maxBase + Randomizer.nextInt(Math.max(1, (int) (maxBase / 10))));

        mob.damage(bot.getCharacter(), damage, true);
        return true;
    }
}
