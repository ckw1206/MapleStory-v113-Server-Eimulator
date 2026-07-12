package server.bot;

import client.MapleCharacter;
import client.MapleClient;
import handling.channel.ChannelServer;
import server.maps.MapleMap;
import server.MaplePortal;
import server.maps.MapleMapFactory;
import server.movement.LifeMovementFragment;
import server.movement.StaticLifeMovement;
import tools.MaplePacketCreator;
import tools.MockIOSession;
import java.awt.Point;
import java.util.Collections;
import java.util.List;

public class BotCharacter {

    private final MapleCharacter character;
    private final MapleClient client;

    public BotCharacter(int botCharId) {
        this.client = new MapleClient(null, null, new MockIOSession());
        int channel = 1;
        client.setChannel(channel);
        this.character = MapleCharacter.loadCharFromDB(botCharId, client, true);
        client.setPlayer(character);
    }

    public boolean spawn(int mapId) {
        if (character.getMap() != null) {
            despawn();
        }
        if (character.getStat().getHp() <= 0) {
            character.getStat().setHp(character.getStat().getMaxHp());
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
        Point newPos = new Point(x, y);
        Point oldPos = character.getPosition();

        StaticLifeMovement movement = new StaticLifeMovement(0, newPos, 0, 1, 0);
        movement.defaulted();
        movement.setPixelsPerSecond(new Point(0, 0));

        List<LifeMovementFragment> moves = Collections.singletonList(movement);

        character.getMap().broadcastMessage(
                character,
                MaplePacketCreator.movePlayer(character.getId(), moves, oldPos),
                false);

        character.getMap().movePlayer(character, newPos);
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

    public int damage(int amount) {
        int currentHp = character.getStat().getHp();
        int actual = Math.min(amount, currentHp);
        if (actual > 0) {
            character.addHP(-actual);
        }
        return actual;
    }

    public int getHp() {
        return character.getStat().getHp();
    }

    public int getMaxHp() {
        return character.getStat().getMaxHp();
    }

    public void despawn() {
        MapleMap map = character.getMap();
        if (map != null) {
            map.removePlayer(character);
        }
    }
}
