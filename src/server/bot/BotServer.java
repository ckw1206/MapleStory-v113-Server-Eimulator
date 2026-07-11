package server.bot;

import io.netty.bootstrap.ServerBootstrap;
import io.netty.channel.*;
import io.netty.channel.nio.NioEventLoopGroup;
import io.netty.channel.socket.SocketChannel;
import io.netty.channel.socket.nio.NioServerSocketChannel;
import io.netty.handler.codec.http.*;
import io.netty.handler.codec.http.websocketx.TextWebSocketFrame;
import io.netty.handler.codec.http.websocketx.WebSocketFrame;
import io.netty.handler.codec.http.websocketx.WebSocketServerProtocolHandler;
import io.netty.util.ReferenceCountUtil;
import server.ServerProperties;
import server.Timer.EtcTimer;
import server.Timer.MobTimer;
import client.MapleCharacter;
import server.bot.json.JsonObject;
import server.bot.json.JsonValue;

import java.net.URLDecoder;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ScheduledFuture;

public class BotServer {

    private static final BotServer INSTANCE = new BotServer();

    public static BotServer getInstance() { return INSTANCE; }

    private ServerBootstrap bootstrap;
    private EventLoopGroup bossGroup, workerGroup;
    private final ConcurrentHashMap<String, BotSession> sessions = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, ScheduledFuture<?>> snapshotTimers = new ConcurrentHashMap<>();
    private final ConcurrentHashMap<String, ScheduledFuture<?>> touchDamageTimers = new ConcurrentHashMap<>();
    private volatile boolean started;

    private BotServer() {}

    public void start() {
        if (started) return;
        int port = ServerProperties.getBotPort();
        bossGroup = new NioEventLoopGroup(1);
        workerGroup = new NioEventLoopGroup();

        bootstrap = new ServerBootstrap()
            .group(bossGroup, workerGroup)
            .channel(NioServerSocketChannel.class)
            .option(ChannelOption.SO_BACKLOG, 128)
            .childOption(ChannelOption.TCP_NODELAY, true)
            .childOption(ChannelOption.SO_KEEPALIVE, true)
            .childHandler(new ChannelInitializer<SocketChannel>() {
                @Override
                protected void initChannel(SocketChannel ch) throws Exception {
                    ChannelPipeline pipe = ch.pipeline();
                    pipe.addLast("http-codec", new HttpServerCodec());
                    pipe.addLast("aggregator", new HttpObjectAggregator(65536));
                    pipe.addLast("handshake-check", new HandshakeValidator());
                    pipe.addLast("ws-protocol", new WebSocketServerProtocolHandler("/ws", null, true, 65536, false, true));
                    pipe.addLast("session-handler", new BotSessionHandler());
                }
            });

        Channel ch;
        try {
            // binds all interfaces because docker port-mapping needs it; token auth is the boundary
            ch = bootstrap.bind(port).sync().channel();
            started = true;
            System.out.println("Bot WS server listening on port " + port);
        } catch (Exception e) {
            e.printStackTrace();
            return;
        }
        ch.closeFuture().addListener(new ChannelFutureListener() {
            @Override public void operationComplete(ChannelFuture f) {
                bossGroup.shutdownGracefully();
                workerGroup.shutdownGracefully();
            }
        });
    }

    public void stop() {
        if (!started) return;
        for (BotSession s : sessions.values()) {
            s.close();
        }
        sessions.clear();
        bossGroup.shutdownGracefully();
        workerGroup.shutdownGracefully();
        started = false;
        System.out.println("Bot WS server stopped");
    }

    void registerSession(String channelId, BotSession session) {
        sessions.put(channelId, session);
    }

    void removeSession(String channelId) {
        sessions.remove(channelId);
        ScheduledFuture<?> f = snapshotTimers.remove(channelId);
        if (f != null) f.cancel(false);
        ScheduledFuture<?> td = touchDamageTimers.remove(channelId);
        if (td != null) td.cancel(false);
    }

    public void startSnapshotBroadcaster(BotSession session) {
        String id = session.getChannelId();
        ScheduledFuture<?> existing = snapshotTimers.get(id);
        if (existing != null && !existing.isDone()) return;

        ScheduledFuture<?> f = EtcTimer.getInstance().register(new Runnable() {
            @Override public void run() {
                BotSession s = sessions.get(id);
                if (s == null || s.getBot() == null || s.getBot().getMap() == null) {
                    ScheduledFuture<?> tf = snapshotTimers.remove(id);
                    if (tf != null) tf.cancel(false);
                    return;
                }
                try {
                    JsonValue snapshot = PerceptionBuilder.buildSnapshot(s.getBot());
                    s.sendSnapshot(snapshot);
                } catch (Exception e) {
                    e.printStackTrace();
                }
            }
        }, 1000);

        snapshotTimers.put(id, f);
    }

    public void onPlayerChat(MapleCharacter chr, String text) {
        if (!started) return;
        for (BotSession s : sessions.values()) {
            try {
                BotCharacter bot = s.getBot();
                if (bot == null || bot.getMap() == null) continue;
                if (bot.getMap() != chr.getMap()) continue;
                if (chr.getId() == bot.getId()) continue;
                JsonObject data = new JsonObject();
                data.put("senderId", chr.getId());
                data.put("senderName", chr.getName());
                data.put("text", text);
                s.sendEvent("chat", data);
            } catch (Exception e) {
            }
        }
    }

    public void startTouchDamageSimulator(BotSession session) {
        String id = session.getChannelId();
        ScheduledFuture<?> existing = touchDamageTimers.get(id);
        if (existing != null && !existing.isDone()) return;

        TouchDamageSimulator sim = new TouchDamageSimulator(session);

        ScheduledFuture<?> f = MobTimer.getInstance().register(sim, 500);
        touchDamageTimers.put(id, f);
    }

    private class HandshakeValidator extends ChannelInboundHandlerAdapter {
        @Override
        public void channelRead(ChannelHandlerContext ctx, Object msg) throws Exception {
            if (!(msg instanceof FullHttpRequest)) {
                ctx.fireChannelRead(msg);
                return;
            }
            FullHttpRequest req = (FullHttpRequest) msg;
            String expectedToken = ServerProperties.getBotToken();
            String providedToken = null;
            String uri = req.uri();
            if (uri != null && uri.indexOf('?') >= 0) {
                String qs = uri.substring(uri.indexOf('?') + 1);
                for (String param : qs.split("&")) {
                    int eq = param.indexOf('=');
                    if (eq > 0 && "token".equals(param.substring(0, eq))) {
                        providedToken = URLDecoder.decode(param.substring(eq + 1), "UTF-8");
                        break;
                    }
                }
            }
            if (expectedToken == null || expectedToken.isEmpty() || !expectedToken.equals(providedToken)) {
                FullHttpResponse res = new DefaultFullHttpResponse(HttpVersion.HTTP_1_1, HttpResponseStatus.UNAUTHORIZED);
                res.headers().set(HttpHeaders.Names.CONNECTION, HttpHeaders.Values.CLOSE);
                ctx.writeAndFlush(res).addListener(ChannelFutureListener.CLOSE);
                ReferenceCountUtil.release(msg);
                return;
            }
            ctx.fireChannelRead(msg);
        }
    }

    private class BotSessionHandler extends SimpleChannelInboundHandler<WebSocketFrame> {
        @Override
        public void userEventTriggered(ChannelHandlerContext ctx, Object evt) throws Exception {
            if (evt instanceof WebSocketServerProtocolHandler.HandshakeComplete) {
                BotSession session = new BotSession(ctx.channel());
                registerSession(ctx.channel().id().asLongText(), session);
            }
            ctx.fireUserEventTriggered(evt);
        }

        @Override
        public void handlerRemoved(ChannelHandlerContext ctx) {
            String channelId = ctx.channel().id().asLongText();
            BotSession session = sessions.get(channelId);
            removeSession(channelId);
            if (session != null) session.onDisconnect();
        }

        @Override
        public void exceptionCaught(ChannelHandlerContext ctx, Throwable cause) {
            cause.printStackTrace();
            ctx.channel().close();
        }

        @Override
        protected void channelRead0(ChannelHandlerContext ctx, WebSocketFrame msg) throws Exception {
            if (msg instanceof TextWebSocketFrame) {
                TextWebSocketFrame frame = (TextWebSocketFrame) msg;
                BotSession session = sessions.get(ctx.channel().id().asLongText());
                if (session != null) {
                    session.onMessage(frame.text());
                }
            }
        }
    }
}
