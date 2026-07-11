package server.bot;

import client.MapleCharacter;
import client.MapleClient;
import handling.channel.ChannelServer;
import server.maps.MapleMap;
import server.maps.MapleMapFactory;
import tools.MockIOSession;
import java.awt.Point;

public class BotCharacter {

    private final MapleCharacter character;
    private final MapleClient client;

    public BotCharacter(int botCharId) {
        this.client = new MapleClient(null, null, new MockIOSession());
        int channel = 1;
        client.setChannel(channel);
        this.character = MapleCharacter.loadCharFromDB(botCharId, client, true);
    }

    public void spawn(int mapId) {
        ChannelServer cs = ChannelServer.getInstance(client.getChannel());
        MapleMapFactory mf = cs.getMapFactory();
        MapleMap map = mf.getMap(mapId);
        map.addPlayer(character);
    }

    public void moveTo(int x, int y) {
        character.getMap().movePlayer(character, new Point(x, y));
    }

    public Point getPosition() {
        return character.getPosition();
    }

    public MapleMap getMap() {
        return character.getMap();
    }

    public int damage(int amount) {
        int currentHp = character.getStat().getHp();
        int actual = Math.min(amount, currentHp);
        character.addHP(-actual);
        return actual;
    }

    public int getHpPercent() {
        int hp = character.getStat().getHp();
        int maxHp = character.getStat().getMaxHp();
        return maxHp == 0 ? 100 : hp * 100 / maxHp;
    }

    public int getLevel() {
        return character.getLevel();
    }

    public int getId() {
        return character.getId();
    }

    public MapleCharacter getCharacter() {
        return character;
    }

    public void despawn() {
        MapleMap map = character.getMap();
        if (map != null) {
            map.removePlayer(character);
        }
    }
}