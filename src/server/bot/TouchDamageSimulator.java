package server.bot;

import server.bot.json.JsonObject;
import server.life.MapleLifeFactory;
import server.life.MapleMonster;
import server.maps.MapleMap;
import server.maps.MapleMapObject;
import server.maps.MapleMapObjectType;

import java.util.Collections;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;

public class TouchDamageSimulator implements Runnable {

    private final BotSession session;
    private final ConcurrentHashMap<Integer, Long> lastHitTime = new ConcurrentHashMap<>();

    public TouchDamageSimulator(BotSession session) {
        this.session = session;
    }

    @Override
    public void run() {
        tick();
    }

    private void tick() {
        BotCharacter bot = session.getBot();
        if (bot == null || bot.getMap() == null) {
            return;
        }

        MapleMap map = bot.getMap();

        boolean hasRealPlayer = false;
        for (client.MapleCharacter chr : map.getCharacters()) {
            if (!chr.isClone() && !chr.isHidden() && chr.getId() != bot.getId()) {
                hasRealPlayer = true;
                break;
            }
        }
        if (!hasRealPlayer) {
            return;
        }

        pruneStaleEntries();

        List<MapleMapObject> mobs = map.getMapObjectsInRange(
                bot.getPosition(), 50.0,
                Collections.singletonList(MapleMapObjectType.MONSTER));

        long now = System.currentTimeMillis();

        for (MapleMapObject mo : mobs) {
            MapleMonster mob = (MapleMonster) mo;
            if (!mob.isAlive()) {
                continue;
            }

            int oid = mob.getObjectId();
            Long lastHit = lastHitTime.get(oid);
            if (lastHit != null && now - lastHit < 1000) {
                continue;
            }

            if (bot.getHp() <= 0) {
                continue;
            }

            int pad = MapleLifeFactory.getPADamage(mob.getId(), mob.getStats().getLevel());
            int actual = bot.damage(pad);
            lastHitTime.put(oid, now);

            if (actual > 0) {
                JsonObject extra = new JsonObject();
                extra.put("damage", actual);
                extra.put("mobId", mob.getId());
                extra.put("hp", bot.getHp());
                extra.put("maxHp", bot.getMaxHp());
                session.sendEvent("damaged", extra);
            }

            if (bot.getHp() <= 0) {
                JsonObject extra = new JsonObject();
                session.sendEvent("died", extra);
                break;
            }
        }
    }

    private void pruneStaleEntries() {
        long cutoff = System.currentTimeMillis() - 30000L;
        Iterator<Map.Entry<Integer, Long>> it = lastHitTime.entrySet().iterator();
        while (it.hasNext()) {
            if (it.next().getValue() < cutoff) {
                it.remove();
            }
        }
    }
}