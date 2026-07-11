/*
 * Minimal JSON parser — original implementation for bot API use.
 * Supports: objects, arrays, strings, numbers, booleans, null.
 */
package server.bot.json;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

public class JsonParser {

    private final String s;
    private int pos = 0;

    public JsonParser(String s) {
        this.s = s;
    }

    public static JsonValue parse(String s) {
        return new JsonParser(s).parseValue();
    }

    private char peek() {
        if (pos >= s.length()) throw new RuntimeException("Unexpected end of JSON at " + pos);
        return s.charAt(pos);
    }
    private char next() {
        if (pos >= s.length()) throw new RuntimeException("Unexpected end of JSON at " + pos);
        return s.charAt(pos++);
    }
    private boolean hasMore() { return pos < s.length(); }

    private JsonValue parseValue() {
        skipWhitespace();
        char c = peek();
        switch (c) {
            case '{': return parseObject();
            case '[': return parseArray();
            case '"': return parseString();
            case 't': return parseKeyword("true",  JsonValue.TRUE);
            case 'f': return parseKeyword("false", JsonValue.FALSE);
            case 'n': return parseKeyword("null",  JsonValue.NULL);
            default:  return parseNumber();
        }
    }

    private void skipWhitespace() {
        while (hasMore()) {
            char c = peek();
            if (c == ' ' || c == '\t' || c == '\n' || c == '\r') {
                pos++;
            } else break;
        }
    }

    private JsonValue parseObject() {
        pos++; // skip '{'
        skipWhitespace();
        Map<String, JsonValue> map = new LinkedHashMap<>();
        if (peek() != '}') {
            while (true) {
                skipWhitespace();
                String key = parseString().getString();
                skipWhitespace();
                if (next() != ':') throw new RuntimeException("Expected ':' at " + pos);
                skipWhitespace();
                JsonValue val = parseValue();
                map.put(key, val);
                skipWhitespace();
                if (next() == '}') break;
            }
        } else {
            pos++; // skip '}'
        }
        return JsonValue.object(map);
    }

    private JsonValue parseArray() {
        pos++; // skip '['
        skipWhitespace();
        List<JsonValue> list = new ArrayList<>();
        if (peek() != ']') {
            while (true) {
                skipWhitespace();
                list.add(parseValue());
                skipWhitespace();
                if (next() == ']') break;
            }
        } else {
            pos++;
        }
        return JsonValue.array(list);
    }

    private JsonValue parseString() {
        pos++; // skip opening '"'
        StringBuilder sb = new StringBuilder();
        while (peek() != '"') {
            char c = next();
            if (c == '\\') {
                char nc = next();
                switch (nc) {
                    case '"':  sb.append('"');  break;
                    case '\\': sb.append('\\'); break;
                    case '/':  sb.append('/');  break;
                    case 'b':  sb.append('\b'); break;
                    case 'f':  sb.append('\f'); break;
                    case 'n':  sb.append('\n'); break;
                    case 'r':  sb.append('\r'); break;
                    case 't':  sb.append('\t'); break;
                    case 'u':
                        if (pos + 4 > s.length()) throw new RuntimeException("Unexpected end of JSON at " + pos);
                        sb.append((char) Integer.parseInt(s.substring(pos, pos + 4), 16));
                        pos += 4;
                        break;
                    default: throw new RuntimeException("Invalid escape \\" + nc + " at " + pos);
                }
            } else {
                sb.append(c);
            }
        }
        pos++; // skip closing '"'
        return JsonValue.string(sb.toString());
    }

    private JsonValue parseNumber() {
        int start = pos;
        if (peek() == '-') pos++;
        while (hasMore()) {
            char c = peek();
            if (Character.isDigit(c)) {
                pos++;
            } else break;
        }
        if (hasMore() && peek() == '.') {
            pos++;
            while (hasMore() && Character.isDigit(peek())) pos++;
        }
        if (hasMore() && (peek() == 'e' || peek() == 'E')) {
            pos++;
            if (hasMore() && (peek() == '+' || peek() == '-')) pos++;
            while (hasMore() && Character.isDigit(peek())) pos++;
        }
        String raw = s.substring(start, pos);
        return JsonValue.number(raw);
    }

    private JsonValue parseKeyword(String expected, JsonValue value) {
        for (int i = 0; i < expected.length(); i++) {
            if (next() != expected.charAt(i)) {
                throw new RuntimeException("Expected " + expected + " at " + pos);
            }
        }
        return value;
    }
}
