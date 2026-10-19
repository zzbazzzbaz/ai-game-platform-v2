# deploy —— 服务器部署

先应用仓库根 `AGENTS.md`，再应用本文件。

服务器 `43.129.212.75`（腾讯云**轻量**香港，2 vCPU / 3.6 GiB + 2 GiB swap，Ubuntu 24.04），
部署根 `/srv/ai-game-platform`（属主 = 部署用户 `guoqitong`，已在 docker 组），
域名 `ai-game-platform.test.chatgqt.top`（Caddy 自动申请/续期 Let's Encrypt 证书，80 → https 308 跳转）。

## 文件职责

| 路径 | 作用 | 谁在用 |
|---|---|---|
| `docker-compose.yml` | 服务器全部 7 个容器 | `scripts/deploy.sh` / 手工 `docker compose` |
| `caddy/Caddyfile` | 系统级 Caddy：HTTPS + 按路径同源反代 | 软链为 `/etc/caddy/Caddyfile` |
| `docker/{api,agent,web}.Dockerfile` | 三个业务镜像，构建上下文分别是 `apps/api`、`apps/agent`、`apps/frontent-test-1` | **只在 CI 构建**，服务器从不构建镜像 |
| `initdb/*.sh` | 游戏库首启初始化（管理员角色、强制 `hostssl`） | `postgres-games` **空数据卷**首启时按文件名顺序执行 |
| `scripts/bootstrap.sh` | 一次性初始化：docker 组、装 Caddy、目录与权限、自签证书、JWT 密钥、systemd 单元 | 手工 `sudo` 跑，幂等 |
| `scripts/deploy.sh` | 部署与回滚的唯一入口 | CI（`cd.yml`）与手工 |
| `scripts/backup.sh` | 备份平台库与游戏库并传 COS，本机留 7 天 | systemd timer `ai-game-backup.timer`（每日 04:00，`Persistent=true`） |

服务器本地文件（**不进 git**）：`.env`（600，唯一业务配置源）、`caddy.env`（`DOMAIN`/`ACME_EMAIL`，644，由 systemd drop-in `caddy.service.d/override.conf` 注入）、
`secrets/jwt/`（JWT 密钥对）、`secrets/pg-tls/`（游戏库自签证书）、`backups/`（dump + `backup.log`）。

## 容器、端口与网络

| 服务 | 镜像 | 端口 | 网络 | 内存上限 |
|---|---|---|---|---|
| `web` | `${WEB_IMAGE}:${TAG}` | `127.0.0.1:8081` → 80 | app | 128m |
| `api` | `${API_IMAGE}:${TAG}` | `127.0.0.1:8082` → 8000 | app, data | 768m |
| `agent` | `${AGENT_IMAGE}:${TAG}` | `127.0.0.1:8083` → 8000 | app, data | 1536m |
| `postgres-games` | `postgres:17.11` | **`0.0.0.0:10050`** → 5432 | data | 512m |
| `postgres-platform` | `postgres:17.11` | 不发布 | data | 384m |
| `langgraph-pg` | `pgvector/pgvector:pg17` | 不发布 | data | 384m |
| `langgraph-redis` | `redis:7-alpine` | 不发布 | data | 192m |

- 卷：`pg-games-data` / `pg-platform-data` / `langgraph-pg-data`（命名卷，**删卷即删库**）；绑定挂载 `./secrets/jwt:/app/.keys:ro`（api）、`./secrets/pg-tls:/pgtls:ro` 与 `./initdb:/docker-entrypoint-initdb.d:ro`（games）。
- 内存上限合计 ≈ 3.9 GiB > 物理内存 3.6 GiB，靠 swap 兜底：加服务或上调 `mem_limit` 前先算账。
- `PG_ADMIN_*` 指向内网 `postgres-games:5432`（api 开通游戏库用）；`GAME_DB_*` 指向**公网** `43.129.212.75:10050` —— 这个串是拼给沙盒用的，沙盒在 docker 网络之外，只能走公网进来。

## Caddy 路由（公网唯一入口）

| 匹配 | 上游 | 说明 |
|---|---|---|
| `/api/*` | `127.0.0.1:8082` | 平台接口 |
| `/.well-known/jwks.json` | `127.0.0.1:8082` | ⚠️ 不能写成 `/.well-known/*`，会把 ACME http-01 挑战也代理走 |
| `/health` | `127.0.0.1:8082` | 健康检查 |
| `/lg*` | `127.0.0.1:8083` | `handle_path` 去前缀；`flush_interval -1`、`read_timeout 0` 是 SSE 流式的必需项 |
| 其余 | `127.0.0.1:8081` | SPA |

另有 `encode zstd gzip`、`header -Server`、access log 写 `/var/log/caddy/access.log`（滚动 10 MiB × 5）。

## 硬约束

1. **配置只放 `.env`**：compose 的 `${...}` 插值全部来自 `/srv/ai-game-platform/.env`（`docker compose --env-file .env ...`）；新增变量必须同时补进 `apps/.env.example`；`.env` 不进 git、保持 600。
2. **镜像 tag 必须显式**：`TAG=sha-<40 位 commit>`；`deploy.sh` 无默认值，缺失即退出；不写 `latest`。
3. **端口纪律**：`web`/`api`/`agent` 只绑 `127.0.0.1`，公网只经 Caddy；唯一例外是 `postgres-games` 的 `10050`（数据库协议直连，不走 Caddy，强制 TLS）。
4. **文件权限**（容器内以非 root 身份读，`deploy.sh` 每次会兜底修一部分）：
   - `caddy/Caddyfile` 644 —— 600 会让 `systemctl reload caddy` 报 `permission denied`
   - `scripts/*.sh`、`initdb/*.sh` 755；`docker-compose.yml` 644
   - `secrets/jwt/*` 属主 **10001**（api 镜像内 app 用户；uid 写死在 `api.Dockerfile`），`jwt_private.pem` 600
   - `secrets/pg-tls/*` 属主 **999**（postgres 官方镜像内 postgres 用户），`server.key` 600、`server.crt` 644
   - `.env` 600、`caddy.env` 644
5. **改 Caddyfile 必须先 `caddy validate` 再 reload**；reload 走 sudoers 白名单 `sudo -n systemctl reload caddy`，不要 `restart`（会掐断在途 SSE）。
6. **不要在服务器上手改 `docker-compose.yml` / `caddy/` / `initdb/` / `scripts/`**：CD 每次 `scp -r` 覆盖这四个路径。配置改 `.env`，其余改仓库。
7. **`initdb/*.sh` 只在空数据卷执行一次**：改它对已初始化的库无效，需要手工 `psql`，或在确认可丢数据后 `docker compose down -v`（先备份）。
8. **HTTPS 与 issuer 联动**：切域名/切协议要同时改四处 —— `caddy.env` 的 `DOMAIN`、Caddyfile 站点地址、`.env` 的 `JWT_ISSUER` 与 `CORS_ORIGINS`。改 issuer 会让**已签发的 token 全部失效**（需要重新登录），属预期行为。
9. compose 里 flow 风格挂载必须加引号（`volumes: ["pg-platform-data:/var/lib/postgresql/data"]`），否则严格 YAML 解析器（Ruby psych 等）会拒绝。
10. 脚本里 `docker compose exec -T` 会吞 stdin：同一脚本内有 heredoc 时必须 `</dev/null`；反过来 `backup.sh` 的 `docker run` 必须保留 `-i`，否则容器里的 python 读不到脚本。

## 三个镜像的注意点

| 镜像 | 关键点 |
|---|---|
| api | 多阶段 uv 构建（`--frozen --no-dev`）；非 root `10001:10001`；入口是 `fastapi run`（**不是 uvicorn**），`--proxy-headers --forwarded-allow-ips '*'` 才能拿到 Caddy 的 `X-Forwarded-*` |
| agent | 由 `uv run langgraph dockerfile` 生成后固化，基础镜像锚定 `langchain/langgraph-api:0.15.4-py3.14`（不用浮动的 `:3.14`）；运行期需要 `POSTGRES_URI`/`REDIS_URI`（compose 注入）；**`apps/agent/langgraph.json` 变更后必须重新生成** |
| web | node 构建 + nginx 静态托管；`VITE_*` 是**构建期**参数（改值要重新构建镜像）；容器内 nginx 只管 SPA 回落与静态缓存，不做反代 |

## 常用操作

```bash
# 首次初始化（sudo、幂等）
sudo DOMAIN=ai-game-platform.test.chatgqt.top ACME_EMAIL=admin@chatgqt.top bash deploy/scripts/bootstrap.sh
# 然后放 .env：照抄 apps/.env.example，按文件头改 16 项，chmod 600

# 部署 / 回滚（服务器上，幂等）
TAG=sha-<40 位 commit> scripts/deploy.sh
# 只重启某个服务（改完 .env 后）
docker compose --env-file .env up -d api agent
# 状态与日志
docker compose --env-file .env ps
docker compose --env-file .env logs -f --tail=100 api
# Caddy
caddy validate --config caddy/Caddyfile && sudo systemctl reload caddy
journalctl -u caddy -n 50 --no-pager
# 备份
scripts/backup.sh && ls -lh backups/ && systemctl list-timers ai-game-backup.timer
```

```bash
# 从开发机（正常路径：走 GitHub Actions）
gh workflow run cd.yml -f tag=main            # 部署最新一次 CI 构建
gh workflow run cd.yml -f tag=sha-<commit>    # 回滚到某个历史构建
curl -fsS https://ai-game-platform.test.chatgqt.top/health
```

## 排错

| 症状 | 原因 | 处置 |
|---|---|---|
| `docker compose pull` 报 unauthorized | 服务器未登录 GHCR（包为私有） | `cd.yml` 已用任务级 `GITHUB_TOKEN` 登录；手工部署则先 `docker login ghcr.io` |
| `systemctl reload caddy` permission denied | Caddyfile 不是 644 | `chmod 644 caddy/Caddyfile` 后重试 |
| 站点 503 `waiting for deploy` | 只跑了 bootstrap，Caddyfile 还是占位配置 | 执行 `scripts/deploy.sh` |
| 443 不通 / 证书签发失败 | 轻量防火墙未放行 443（续期还需 80） | 控制台放行后 reload；临时可切回 HTTP（见 `caddy/Caddyfile` 顶部注释） |
| 沙盒连不上游戏库 | 远程连接没走 TLS（pg_hba 只剩 `hostssl`）或被 `require` 当成 `verify-full` | 沙盒侧 `GAME_DB_SSLMODE=no-verify` |
| 容器起来就 unhealthy | `.env` 缺变量（配置 fail-fast） | `docker compose --env-file .env logs <svc>` 找到缺失项，补 `.env` 后 `up -d` |
| 备份 timer 没产出 | timer 未启用 / 脚本无执行位 | `systemctl status ai-game-backup.timer`；`chmod 755 scripts/*.sh` |

## 与仓库其余部分的契约

- **唯一配置样板是 `apps/.env.example`**；服务器 `.env` = 照抄后改文件头列出的 16 项。`deploy/` 下不再有第二份样板。
- 前端只发相对路径（`/api/v1`、`/lg`），靠宿主机 Caddy 同源反代；将来换正式前端只需改 `WEB_IMAGE`。
- 三个 Dockerfile 的构建上下文是各工程根目录：工程内新增「运行期需要」的文件必须同步 Dockerfile（否则只在本地能跑）。
- `deploy/` 的改动要生效必须提交并走 CD —— push 只构建镜像，**部署是手动的**（`cd.yml` 的 `workflow_dispatch`）。
- 游戏库的连接串/口令不落库、按 `game_id` 派生，规则见仓库根 `AGENTS.md` 的跨服务契约；`deploy/` 只负责让 `postgres-games` 可达且强制 TLS。
