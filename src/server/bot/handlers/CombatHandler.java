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

        // Derive damage from bot's own stats
        client.PlayerStats ps = bot.getCharacter().getStat();
        int baseDamage = Math.max(1, (ps.getTotalStr() + ps.getDex()) * 2 + ps.getTotalWatk());
        int damage = baseDamage + Randomizer.nextInt(Math.max(1, baseDamage / 10));

        mob.damage(bot.getCharacter(), damage, true);
        return true;
    }

    @Override
    public String getCapabilityName() { return "combat"; }
}