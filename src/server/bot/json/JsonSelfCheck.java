package server.bot.json;

public class JsonSelfCheck {

    public static void main(String[] args) {
        JsonObject intTest = new JsonObject();
        intTest.put("seq", 42);
        String intJson = intTest.toString();
        if (intJson.contains("42.0")) {
            System.out.println("FAIL: int serialized as 42.0");
            System.exit(1);
        }

        String json = "{" +
            "\"obj\":{\"key\":\"val\"}," +
            "\"arr\":[1,2,3]," +
            "\"str\":\"hello\\\"world\\ntest\"," +
            "\"num\":42.5," +
            "\"bool\":true," +
            "\"null\":null" +
        "}";

        JsonValue v1 = JsonParser.parse(json);
        String reencoded = v1.toString();
        JsonValue v2 = JsonParser.parse(reencoded);

        if (!valuesEqual(v1, v2)) {
            System.out.println("FAIL");
            System.exit(1);
        }

        try {
            JsonParser.parse("{\"action\":");
            System.out.println("FAIL: truncated input 1 should throw");
            System.exit(1);
        } catch (RuntimeException e) {
            // expected
        }

        try {
            JsonParser.parse("{");
            System.out.println("FAIL: truncated input 2 should throw");
            System.exit(1);
        } catch (RuntimeException e) {
            // expected
        }

        System.out.println("OK");
    }

    private static boolean valuesEqual(JsonValue a, JsonValue b) {
        if (a == b) return true;
        if (a == null || b == null) return false;
        if (a.getType() != b.getType()) return false;
        switch (a.getType()) {
            case T_STRING: return a.getString().equals(b.getString());
            case T_NUMBER: return a.getDouble() == b.getDouble();
            case T_TRUE: case T_FALSE: return a.getBoolean() == b.getBoolean();
            case T_NULL: return true;
            case T_OBJECT: {
                JsonObject oa = (JsonObject) a, ob = (JsonObject) b;
                if (oa.size() != ob.size()) return false;
                for (String k : oa.keys()) {
                    if (!valuesEqual(oa.get(k), ob.get(k))) return false;
                }
                return true;
            }
            case T_ARRAY: {
                JsonArray oa = (JsonArray) a, ob = (JsonArray) b;
                if (oa.size() != ob.size()) return false;
                for (int i = 0; i < oa.size(); i++) {
                    if (!valuesEqual(oa.get(i), ob.get(i))) return false;
                }
                return true;
            }
            default: return false;
        }
    }
}
