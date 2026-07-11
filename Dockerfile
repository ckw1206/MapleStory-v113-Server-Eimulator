# Java 11, not 17+: the scripting engine is Nashorn (AbstractScriptManager), which
# was removed from the JDK in Java 15 and dist/ has no standalone nashorn jar.
FROM eclipse-temurin:11-jdk AS build
WORKDIR /app
COPY src ./src
COPY dist ./dist
RUN javac -encoding UTF-8 -d . -cp "dist/*" $(find src -name '*.java')

FROM eclipse-temurin:11-jre
WORKDIR /app
COPY dist ./dist
COPY --from=build /app/client ./client
COPY --from=build /app/constants ./constants
COPY --from=build /app/database ./database
COPY --from=build /app/handling ./handling
COPY --from=build /app/provider ./provider
COPY --from=build /app/scripting ./scripting
COPY --from=build /app/server ./server
COPY --from=build /app/tools ./tools

# wz/ and Settings.ini are mounted at runtime (see docker-compose.yml) rather than
# baked in: wz is ~750MB of game assets and Settings.ini holds per-deployment config.
CMD ["java", "-Xmx512M", "-server", "-Dnashorn.args=--no-deprecation-warning", "-Dnet.sf.odinms.wzpath=wz", "-cp", ".:dist/*", "server.Start"]
