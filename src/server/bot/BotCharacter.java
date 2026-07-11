package server.bot;

import client.MapleCharacter;
import client.MapleClient;
import handling.channel.ChannelServer;
import server.maps.MapleMap;
import server.MaplePortal;
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

    public boolean spawn(int mapId) {
        if (character.getMap() != null) {
            despawn();
        }
        ChannelServer cs = ChannelServer.getInstance(client.getChannel());
        MapleMapFactory mf = cs.getMapFactory();
        MapleMap map = mf.getMap(mapId);
        if (map == null) {
            return false;
        }
        MaplePortal sp = map.getPortal(0);
        character.setMap(map);
        character.setPosition(sp.getPosition());
        map.addPlayer(character);
        return true;
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

    public int getLevel() {
        return character.getLevel();
    }

    public boolean isLoaded() { return character != null; }

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
