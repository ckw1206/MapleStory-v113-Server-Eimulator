package server.bot;

import java.io.File;
import provider.MapleData;
import provider.MapleDataProvider;
import provider.MapleDataProviderFactory;
import provider.MapleDataTool;

public class MobPADamage {

    private static final MapleDataProvider MOB_DATA = MapleDataProviderFactory.getDataProvider(
            new File(System.getProperty("net.sf.odinms.wzpath") + "/Mob.wz"));

    public static int getPADamage(int mobId, int level) {
        try {
            MapleData mobNode = MOB_DATA.getData(String.valueOf(mobId));
            if (mobNode == null) {
                return fallback(level);
            }
            int pad = MapleDataTool.getIntConvert("info/PADamage", mobNode, -1);
            if (pad == -1) {
                return fallback(level);
            }
            return Math.max(1, pad);
        } catch (Exception e) {
            return fallback(level);
        }
    }

    private static int fallback(int level) {
        return Math.max(1, level * 5 + 10);
    }
}