# MapleStory v113 Server Emulator

台服 113 伺服器，原始來源為網路，更新為 Netty 架構。會不定時修正伺服器，至於 NPC 腳本有請大家補充，有任何 BUG 請善用 issues。

## Quick start (Docker)

Runs MySQL and the game server together, no local JDK required.

```sh
make setup      # copy .env.example / Settings.ini.example if missing
make docker-up  # build the server image, start MySQL + the server
```

Edit `.env` and `Settings.ini` first if you need non-default credentials or world
settings. If the server is running in Docker, set `tms.Url` in `Settings.ini` to use
host `mysql` instead of `localhost` (see comment in `Settings.ini.example`) - it
reaches the MySQL container over the compose network rather than the published port.

Other targets: `make docker-down`, `make docker-logs`, `make docker-build` (rebuild
after code changes). Run `make help` for the full list, including the native
(non-Docker) `build`/`start`/`stop` flow.

## Requirements

- Docker + Docker Compose, **or** JDK 8–14 (all dependencies ship as jars in `dist/`)
  for the native flow. Not JDK 15+: the game scripts run on Nashorn, which was removed
  from the JDK in Java 15. The Docker image uses Java 11.

## 目前已修正

1. 多人遊戲
2. 廣播
3. 商城
4. 多數技能（召喚獸斷線、各式技能 BUFF 失效、異常斷線、海盜船生命、龍之獻技異常扣血）
5. 修正部分計時器殘留問題
6. 登入複製
7. 釣魚
8. 個人資料
9. 部分商城消耗道具（AP、SP 捲，原地復活，高級卷...不一一列表）
10. 宅配物品紀錄 15 日，超過 15 日將會刪除
11. 經驗書
12. 成長武器
13. 時空門位置異常
14. 微調封鎖機制
15. 生命類御守（或許是錯誤的 Wz 檔）
16. 騎寵疲勞度
17. 火毒毒霧傷害
18. 商城寵物技能
19. 精靈商人留言功能

## License

MIT License.
