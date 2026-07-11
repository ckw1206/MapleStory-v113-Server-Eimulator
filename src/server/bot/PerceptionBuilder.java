package server.bot;

import client.MapleCharacter;
import client.inventory.IItem;
import client.inventory.MapleInventory;
import client.inventory.MapleInventoryType;
import server.bot.json.JsonArray;
import server.bot.json.JsonObject;
import server.bot.json.JsonValue;
import server.life.MapleMonster;
import server.maps.MapleMap;
import server.maps.MapleMapItem;
import server.maps.MapleMapObject;
import server.maps.MapleMapObjectType;
import server.MaplePortal;

import java.util.Collection;
import java.util.Collections;
import java.util.List;

public class PerceptionBuilder {

    public static JsonValue buildSnapshot(BotCharacter bot) {
        MapleMap map = bot.getMap();
        JsonObject snap = new JsonObject();

        snap.put("mapId", map.getId());
        JsonObject pos = new JsonObject();
        pos.put("x", (int) bot.getPosition().getX());
        pos.put("y", (int) bot.getPosition().getY());
        snap.put("position", pos);

        MapleCharacter chr = bot.getCharacter();
        snap.put("hp", chr.getStat().getHp());
        snap.put("maxHp", chr.getStat().getMaxHp());
        snap.put("mp", chr.getStat().getMp());
        snap.put("maxMp", chr.getStat().getMaxMp());
        snap.put("level", bot.getLevel());

        JsonArray invArr = new JsonArray();
        for (MapleInventoryType invType : MapleInventoryType.values()) {
            MapleInventory inv = chr.getInventory(invType);
            for (IItem item : inv.list()) {
                JsonObject itemObj = new JsonObject();
                itemObj.put("type", invType.name());
                itemObj.put("id", item.getItemId());
                itemObj.put("qty", item.getQuantity());
                invArr.getList().add(itemObj);
            }
        }
        snap.put("inventorySummary", invArr);

        List<MapleMapObject> mobs = map.getMapObjectsInRange(
                bot.getPosition(), 1500.0,
                Collections.singletonList(MapleMapObjectType.MONSTER));
        JsonArray mobsArr = new JsonArray();
        for (MapleMapObject mo : mobs) {
            MapleMonster mob = (MapleMonster) mo;
            if (!mob.isAlive()) continue;
            JsonObject mobObj = new JsonObject();
            mobObj.put("id", mob.getId());
            mobObj.put("oid", mob.getObjectId());
            mobObj.put("x", (int) mob.getPosition().getX());
            mobObj.put("y", (int) mob.getPosition().getY());
            double hpPct = mob.getHp() * 100.0 / mob.getMobMaxHp();
            mobObj.put("hpPct", (int) hpPct);
            mobsArr.getList().add(mobObj);
        }
        snap.put("mobs", mobsArr);

        List<MapleMapObject> drops = map.getMapObjectsInRange(
                bot.getPosition(), 1500.0,
                Collections.singletonList(MapleMapObjectType.ITEM));
        JsonArray dropsArr = new JsonArray();
        for (MapleMapObject mo : drops) {
            MapleMapItem drop = (MapleMapItem) mo;
            if (drop.isPickedUp()) continue;
            JsonObject dropObj = new JsonObject();
            dropObj.put("oid", drop.getObjectId());
            dropObj.put("itemId", drop.getItem().getItemId());
            dropObj.put("x", (int) drop.getPosition().getX());
            dropObj.put("y", (int) drop.getPosition().getY());
            dropsArr.getList().add(dropObj);
        }
        snap.put("drops", dropsArr);

        Collection<MapleCharacter> players = map.getCharacters();
        JsonArray playersArr = new JsonArray();
        for (MapleCharacter p : players) {
            if (p.isClone() || p.isHidden()) continue;
            if (p.getId() == bot.getId()) continue;
            JsonObject pObj = new JsonObject();
            pObj.put("id", p.getId());
            pObj.put("name", p.getName());
            pObj.put("x", (int) p.getPosition().getX());
            pObj.put("y", (int) p.getPosition().getY());
            playersArr.getList().add(pObj);
        }
        snap.put("players", playersArr);

        JsonArray portalsArr = new JsonArray();
        for (MaplePortal p : map.getPortals()) {
            JsonObject pObj = new JsonObject();
            pObj.put("name", p.getName());
            pObj.put("x", (int) p.getPosition().getX());
            pObj.put("y", (int) p.getPosition().getY());
            portalsArr.getList().add(pObj);
        }
        snap.put("portals", portalsArr);

        return snap;
    }
}