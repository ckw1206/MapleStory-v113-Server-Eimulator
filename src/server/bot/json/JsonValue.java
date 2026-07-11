/*
 * Minimal JSON parser — MIT License
 * https://github.com/ralfstx/minimal-json
 * Ported to single-filevendored form for bot API use.
 */
package server.bot.json;

public abstract class JsonValue {

    public enum Type { T_STRING, T_NUMBER, T_OBJECT, T_ARRAY, T_TRUE, T_FALSE, T_NULL }

    private final Type type;

    protected JsonValue(Type type) {
        this.type = type;
    }

    public Type getType() { return type; }

    public boolean isObject()  { return type == Type.T_OBJECT; }
    public boolean isArray()   { return type == Type.T_ARRAY; }
    public boolean isString()  { return type == Type.T_STRING; }
    public boolean isNumber()  { return type == Type.T_NUMBER; }
    public boolean isTrue()    { return type == Type.T_TRUE; }
    public boolean isFalse()   { return type == Type.T_FALSE; }
    public boolean isNull()    { return type == Type.T_NULL; }
    public boolean isBoolean() { return type == Type.T_TRUE || type == Type.T_FALSE; }

    public String getString() {
        throw new UnsupportedOperationException("Not a string: " + type);
    }

    public int getInt() {
        throw new UnsupportedOperationException("Not a number: " + type);
    }

    public long getLong() {
        throw new UnsupportedOperationException("Not a number: " + type);
    }

    public double getDouble() {
        throw new UnsupportedOperationException("Not a number: " + type);
    }

    public boolean getBoolean() {
        throw new UnsupportedOperationException("Not a boolean: " + type);
    }

    public JsonObject getObject() {
        throw new UnsupportedOperationException("Not an object: " + type);
    }

    public JsonArray getArray() {
        throw new UnsupportedOperationException("Not an array: " + type);
    }

    @Override public String toString() {
        StringBuilder sb = new StringBuilder();
        writeTo(sb);
        return sb.toString();
    }

    protected abstract void writeTo(StringBuilder sb);

    // Concrete type classes

    public static final class JsonNumber extends JsonValue {
        private final double value;
        private final String raw;

        public JsonNumber(double value, String raw) {
            super(Type.T_NUMBER);
            this.value = value;
            this.raw = raw;
        }

        @Override public int getInt()    { return (int) value; }
        @Override public long getLong()  { return (long) value; }
        @Override public double getDouble() { return value; }

        @Override protected void writeTo(StringBuilder sb) { sb.append(raw); }
    }

    public static final class JsonString extends JsonValue {
        private final String value;

        public JsonString(String value) {
            super(Type.T_STRING);
            this.value = value;
        }

        @Override public String getString() { return value; }

        @Override protected void writeTo(StringBuilder sb) {
            sb.append('"');
            escapeString(value, sb);
            sb.append('"');
        }

        private static void escapeString(String s, StringBuilder sb) {
            for (int i = 0; i < s.length(); i++) {
                char c = s.charAt(i);
                switch (c) {
                    case '"':  sb.append("\\\""); break;
                    case '\\': sb.append("\\\\"); break;
                    case '\b': sb.append("\\b");  break;
                    case '\f': sb.append("\\f");  break;
                    case '\n': sb.append("\\n");  break;
                    case '\r': sb.append("\\r");  break;
                    case '\t': sb.append("\\t");  break;
                    default:
                        if (c < ' ') {
                            sb.append(String.format("\\u%04x", (int) c));
                        } else {
                            sb.append(c);
                        }
                }
            }
        }
    }

    public static final class JsonObject extends JsonValue {
        private final java.util.Map<String, JsonValue> map;

        public JsonObject(java.util.Map<String, JsonValue> map) {
            super(Type.T_OBJECT);
            this.map = map;
        }

        public JsonValue get(String key)                       { return map.get(key); }
        public String    getString(String key)                 { JsonValue v = map.get(key); return v == null ? null : v.getString(); }
        public String    getString(String key, String def)     { JsonValue v = map.get(key); return v != null && v.isString() ? v.getString() : def; }
        public int       getInt(String key, int def)           { JsonValue v = map.get(key); return v != null && v.isNumber() ? v.getInt() : def; }
        public long      getLong(String key, long def)         { JsonValue v = map.get(key); return v != null && v.isNumber() ? v.getLong() : def; }
        public boolean   getBoolean(String key, boolean def)   { JsonValue v = map.get(key); return v != null && v.isBoolean() ? v.getBoolean() : def; }
        public JsonObject getJsonObject(String key)            { JsonValue v = map.get(key); return v != null && v.isObject() ? v.getObject() : null; }
        public JsonArray  getJsonArray(String key)             { JsonValue v = map.get(key); return v != null && v.isArray() ? v.getArray() : null; }
        public int       size()                                { return map.size(); }
        public boolean   containsKey(String key)               { return map.containsKey(key); }
        public Iterable<String> keys()                         { return map.keySet(); }

        @Override protected void writeTo(StringBuilder sb) {
            sb.append('{');
            boolean first = true;
            for (java.util.Map.Entry<String, JsonValue> e : map.entrySet()) {
                if (!first) sb.append(',');
                first = false;
                sb.append('"').append(e.getKey()).append("\":");
                e.getValue().writeTo(sb);
            }
            sb.append('}');
        }
    }

    public static final class JsonArray extends JsonValue {
        private final java.util.List<JsonValue> list;

        public JsonArray(java.util.List<JsonValue> list) {
            super(Type.T_ARRAY);
            this.list = list;
        }

        public JsonValue get(int index) { return list.get(index); }
        public int size()               { return list.size(); }

        @Override protected void writeTo(StringBuilder sb) {
            sb.append('[');
            for (int i = 0; i < list.size(); i++) {
                if (i > 0) sb.append(',');
                list.get(i).writeTo(sb);
            }
            sb.append(']');
        }
    }

    public static final class JsonBoolean extends JsonValue {
        private final boolean value;
        private JsonBoolean(Type type, boolean value) { super(type); this.value = value; }
        @Override public boolean getBoolean() { return value; }
        @Override protected void writeTo(StringBuilder sb) { sb.append(value ? "true" : "false"); }
    }

    public static final JsonValue TRUE  = new JsonBoolean(Type.T_TRUE,  true);
    public static final JsonValue FALSE = new JsonBoolean(Type.T_FALSE, false);
    public static final JsonValue NULL  = new JsonValue(Type.T_NULL) {
        @Override protected void writeTo(StringBuilder sb) { sb.append("null"); }
    };

    public static JsonValue string(String s)  { return new JsonString(s); }
    public static JsonValue number(double v)  { return new JsonNumber(v, String.valueOf(v)); }
    public static JsonValue number(String raw) {
        return new JsonNumber(Double.parseDouble(raw), raw);
    }
    public static JsonValue object(java.util.Map<String, JsonValue> m) { return new JsonObject(m); }
    public static JsonValue array(java.util.List<JsonValue> l)         { return new JsonArray(l); }
}