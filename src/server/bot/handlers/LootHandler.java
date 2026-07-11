package server.bot.handlers;

import client.MapleCharacter;
import client.inventory.IItem;
import client.inventory.MapleInventory;
import client.inventory.MapleInventoryType;
import server.MapleInventoryManipulator;
import server.MapleItemInformationProvider;
import server.MapleStatEffect;
import server.bot.BotActionHandler;
import server.bot.BotCharacter;
import server.bot.BotSession;
import server.bot.json.JsonObject;
import server.maps.MapleMapItem;
import server.maps.MapleMapObject;
import server.maps.MapleMapObjectType;
import tools.MaplePacketCreator;

public class LootHandler implements BotActionHandler {

    @Override
    public boolean handle(BotSession session, BotCharacter bot, String actionName, JsonObject args) {
        if ("pickup".equals(actionName)) {
            return handlePickup(bot, args);
        } else if ("use_item".equals(actionName)) {
            return handleUseItem(bot, args);
        }
        return false;
    }

    private boolean handlePickup(BotCharacter bot, JsonObject args) {
        int dropOid = args.getInt("dropId", -1);
        if (dropOid == -1) return false;

        MapleMapObject itemObj = bot.getMap().getMapObject(dropOid, MapleMapObjectType.ITEM);
        if (!(itemObj instanceof MapleMapItem)) return false;
        MapleMapItem item = (MapleMapItem) itemObj;
        if (item.isPickedUp()) return false;
        if (item.getOwner() != 0 && item.getOwner() != bot.getId()) return false;

        IItem itemData = item.getItem();
        if (itemData == null) return false;

        boolean added = MapleInventoryManipulator.addFromDrop(bot.getCharacter().getClient(), itemData, false);
        if (added) {
            bot.getMap().broadcastMessage(
                    MaplePacketCreator.removeItemFromMap(item.getObjectId(), 2, bot.getId()),
                    item.getPosition());
            bot.getMap().removeMapObject(item);
        }
        return added;
    }

    private boolean handleUseItem(BotCharacter bot, JsonObject args) {
        int itemId = args.getInt("itemId", -1);
        if (itemId == -1) return false;

        MapleCharacter chr = bot.getCharacter();
        byte invTypeByte = (byte) (itemId / 1000000);
        MapleInventoryType invType = MapleInventoryType.getByType(invTypeByte);
        if (invType == null) return false;

        MapleInventory inv = chr.getInventory(invType);
        IItem found = null;
        for (IItem it : inv.list()) {
            if (it.getItemId() == itemId) {
                found = it;
                break;
            }
        }
        if (found == null) return false;

        MapleItemInformationProvider mmii = MapleItemInformationProvider.getInstance();
        MapleStatEffect itemEffect = mmii.getItemEffect(itemId);
        if (itemEffect == null) return false;

        itemEffect.applyTo(chr);
        MapleInventoryManipulator.removeById(chr.getClient(), invType, itemId, 1, false, false);

        return true;
    }
}
