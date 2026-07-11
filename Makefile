SHELL := /bin/sh

# classpath separator: ';' for Windows java (even under Git Bash), ':' elsewhere
SEP      := $(if $(filter Windows_NT,$(OS)),;,:)
JAVA_CP  := .$(SEP)dist/*
PID_FILE := .server.pid
LOG_FILE := Logs/server.log

.PHONY: help setup build db-up db-down db-logs start stop restart down clean docker-up docker-down docker-logs docker-build

help:
	@echo "make setup        - copy .env.example/Settings.ini.example if missing"
	@echo "make db-up        - start the MySQL container"
	@echo "make db-down      - stop the MySQL container"
	@echo "make db-logs      - tail the MySQL container logs"
	@echo "make build        - compile the server (javac -d .)"
	@echo "make start        - build, start MySQL, then start the server in the background"
	@echo "make stop         - stop the server (MySQL keeps running)"
	@echo "make restart      - stop then start"
	@echo "make down         - stop the server and MySQL"
	@echo "make clean        - remove compiled .class files"
	@echo "make docker-up    - build and start MySQL + the server, both in Docker"
	@echo "make docker-down  - stop the dockerized server and MySQL"
	@echo "make docker-logs  - tail the dockerized server logs"
	@echo "make docker-build - rebuild the server image (after code changes)"

setup:
	@[ -f .env ] || cp .env.example .env
	@[ -f Settings.ini ] || cp Settings.ini.example Settings.ini
	@echo "setup done - edit .env and Settings.ini before starting"

db-up:
	docker compose up -d mysql

db-down:
	docker compose stop mysql

db-logs:
	docker compose logs -f mysql

build:
	javac -encoding UTF-8 -d . -cp "$(JAVA_CP)" $$(find src -name '*.java')

start: db-up build
	@if [ -f $(PID_FILE) ] && kill -0 `cat $(PID_FILE)` 2>/dev/null; then \
		echo "server already running (pid `cat $(PID_FILE)`)"; \
	else \
		mkdir -p Logs; \
		nohup java -Xmx512M -server -Dnet.sf.odinms.wzpath=wz -cp "$(JAVA_CP)" server.Start > $(LOG_FILE) 2>&1 & echo $$! > $(PID_FILE); \
		echo "server started (pid `cat $(PID_FILE)`), logging to $(LOG_FILE)"; \
	fi

stop:
	@if [ -f $(PID_FILE) ]; then \
		kill `cat $(PID_FILE)` 2>/dev/null || true; \
		rm -f $(PID_FILE); \
		echo "server stopped"; \
	else \
		echo "server not running"; \
	fi

restart: stop start

down: stop db-down

clean:
	@find client constants database handling provider scripting server tools -name '*.class' -delete 2>/dev/null || true

docker-up:
	docker compose up -d --build

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f server

docker-build:
	docker compose build server
