/*
 * Minimal JSON object — original implementation for bot API use.
 */
package server.bot.json;

import java.util.Map;

public class JsonObject extends JsonValue {

    private final Map<String, JsonValue> map;

    public JsonObject() {
        this(new java.util.LinkedHashMap<>());
    }

    public JsonObject(Map<String, JsonValue> map) {
        super(Type.T_OBJECT);
        this.map = map;
    }

    public JsonValue get(String key)                       { return map.get(key); }
    public String    getString(String key)                 { JsonValue v = map.get(key); return v == null ? null : v.getString(); }
    public String    getString(String key, String def)     { JsonValue v = map.get(key); return v != null && v.isString() ? v.getString() : def; }
    public int       getInt(String key, int def)           { JsonValue v = map.get(key); return v != null && v.isNumber() ? v.getInt() : def; }
    public long      getLong(String key, long def)         { JsonValue v = map.get(key); return v != null && v.isNumber() ? v.getLong() : def; }
    public boolean   getBoolean(String key, boolean def)   { JsonValue v = map.get(key); return v != null && v.isBoolean() ? v.getBoolean() : def; }
    public JsonObject getJsonObject(String key)            { JsonValue v = map.get(key); return v != null && v.isObject() ? (JsonObject) v : null; }
    public JsonArray  getJsonArray(String key)             { JsonValue v = map.get(key); return v != null && v.isArray() ? (JsonArray) v : null; }
    public int       size()                                { return map.size(); }
    public boolean   containsKey(String key)               { return map.containsKey(key); }
    public Iterable<String> keys()                         { return map.keySet(); }

    public void put(String key, JsonValue value)            { map.put(key, value); }
    public void put(String key, String value)               { map.put(key, JsonValue.string(value)); }
    public void put(String key, int value)                  { map.put(key, JsonValue.number(value)); }
    public void put(String key, long value)                 { map.put(key, JsonValue.number(value)); }
    public void put(String key, boolean value)              { map.put(key, value ? JsonValue.TRUE : JsonValue.FALSE); }

    @Override protected void writeTo(StringBuilder sb) {
        sb.append('{');
        boolean first = true;
        for (Map.Entry<String, JsonValue> e : map.entrySet()) {
            if (!first) sb.append(',');
            first = false;
            sb.append('"').append(e.getKey()).append("\":");
            e.getValue().writeTo(sb);
        }
        sb.append('}');
    }
}
