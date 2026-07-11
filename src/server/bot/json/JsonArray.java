/*
 * Minimal JSON — MIT License
 * https://github.com/ralfstx/minimal-json
 */
package server.bot.json;

import java.util.List;

public class JsonArray extends JsonValue {

    private final List<JsonValue> list;

    public JsonArray() {
        this(new java.util.ArrayList<>());
    }

    public JsonArray(List<JsonValue> list) {
        super(Type.T_ARRAY);
        this.list = list;
    }

    public JsonValue get(int index) { return list.get(index); }
    public int size()               { return list.size(); }
    public List<JsonValue> getList() { return list; }

    @Override protected void writeTo(StringBuilder sb) {
        sb.append('[');
        for (int i = 0; i < list.size(); i++) {
            if (i > 0) sb.append(',');
            list.get(i).writeTo(sb);
        }
        sb.append(']');
    }
}