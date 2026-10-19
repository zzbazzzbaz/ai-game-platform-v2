# AI 游戏平台（v0.2 · 规格 A1）

面向无编程基础用户：与 AI 多轮对话生成「带服务端的可玩游戏」，沙盒内实时预览，一键发布公网。

## 仓库结构

| 路径 | 内容 | 性质 |
|---|---|---|
| `apps/api/` | FastAPI 平台后端；唯一持云凭证与 PG 管理凭证；认证签发方 | Python 工程（uv） |
| `apps/agent/` | LangGraph Server + deepagents；只持沙盒访问权（E2B Key）与内部令牌 | Python 工程（uv） |
| `apps/frontent-test-1/` | 平台前端 SPA（Vite + React）；**过渡用**，后续换正式前端工程（只换 `WEB_IMAGE`） | Node 工程（npm） |
| `sandbox/` | 沙盒资产：`image/`（AGS 自定义镜像 Dockerfile + 启动脚本）、`game-template/`（游戏工程模板）、`assets/skills/`（Phaser 技能库） | 镜像/资产 |
| `deploy/` | 服务器部署：`docker-compose.yml`、`caddy/Caddyfile`、`docker/*.Dockerfile`、`initdb/`、`scripts/` | 部署 |
| `.github/workflows/ci.yml` | CI：push 自动构建推送 GHCR（**不在 CI 里跑测试**，测试本地 `make test`） | CI |
| `.github/workflows/cd.yml` | CD：**只能手动触发**（`gh workflow run cd.yml -f tag=<main\|sha-xxx>`）→ SSH 拉镜像重建 | CD |
| `docs/` | 规格与讨论记录（`docs/db/` 为数据库说明） | 文档 |

## 开发环境拓扑（本阶段）

- **平台元数据库**（`users` / `games` / `game_threads` / `game_versions`）：**本地 Docker PG**（`apps/docker-compose.yml`，`aigame_platform`）。
- **游戏数据库**（每游戏 `game_{sid}` + role `game_{sid}_rw`）：**公网 VPS PG**（`43.129.212.75:10050`，由 api 管理员凭证开通；沙盒经公网直连）。
- AGS 沙盒、COS 桶均为腾讯云端资源（本地开发同样使用）。

## 生产/测试部署拓扑（`deploy/`）

- 服务器 `43.129.212.75`（腾讯云**轻量**香港）；域名 `ai-game-platform.test.chatgqt.top`。
- **HTTPS 已启用**（轻量防火墙已放行 443）：Caddy 自动申请/续期 Let's Encrypt 证书，80 端口自动 308 跳转到 https；
  `JWT_ISSUER`/`CORS_ORIGINS` 均为 `https://<域名>`。⚠️ 证书续期依赖 80/443 长期可从公网访问，
  若 443 被关掉，按 `deploy/caddy/Caddyfile` 顶部注释临时切回 HTTP。
- **公网 HTTP 唯一入口 = 宿主机系统级 Caddy**（systemd，`/etc/caddy/Caddyfile` 软链到 `/srv/ai-game-platform/caddy/Caddyfile`）；容器全部在内网：
  `web`/`api`/`agent` 只绑 `127.0.0.1:8081/8082/8083`，由 Caddy 按路径同源反代（`/api/*`→api、`/lg/*`→agent 去前缀、`/`→web）。
- 数据容器：`postgres-games`（**0.0.0.0:10050**，数据库协议直连不走 Caddy，`hostssl` 强制 TLS）、`postgres-platform`、`langgraph-pg`（pgvector）、`langgraph-redis`（均不发布端口）。
- 配置源：服务器 `/srv/ai-game-platform/.env`（600，不进 git，样板见 `apps/.env.example`）。
- 发布节奏：push 只跑 CI（构建 `sha-<commit>` + `main` 两个 tag），**不自动上生产**；部署手动 `gh workflow run cd.yml -f tag=main`，回滚 `-f tag=sha-<旧 commit>`（等价于服务器上 `TAG=<tag> scripts/deploy.sh`）。
- 镜像：GHCR `ghcr.io/zzbazzzbaz/ai-game-platform-v2/{api,agent,web}`（public）。
- ⚠️ `GAME_DB_SSLMODE` **必须 `no-verify`**：沙盒内 node `pg` 的 `pg-connection-string@2.14` 把 `sslmode=require` 当作 `verify-full`，自签证书下会连不上。

## 跨服务契约（改动必须同步）

- 命名根：`game_id`（UUID）；`sid = game_id 去掉"-"`（32 位十六进制）；所有外部资源命名只由 game_id 推导。
- 沙盒（AGS `custom` 自建镜像 `sandbox/image/`）：`metadata.game_id = game_id`；工作区 `/workspace/work`（COS `games/{game_id}/`，镜像 entrypoint 在空工作区时从 `/opt/game-template` 播种）、素材 `/workspace/input`（只读）、依赖 `/opt/game-template/node_modules`（软链到工作区）、skills `/opt/skills`；浏览器栈 NoVNC `:9000`、envd `:49983`。
- COS 前缀：游戏资产 `games/{game_id}/**`；版本包 `games/{game_id}/versions/{seq}.tar`。
- 托管服务名：`g-{sid}`（云托管服务名上限 36 字符，`game-{game_id}` 超限；仍仅由 game_id 派生）。
- 游戏数据库：`game_{sid}`、role `game_{sid}_rw`，密码 = `base64url(HMAC-SHA256(GAME_DB_PASSWORD_MASTER_SECRET, game_id))`；开通必须 `REVOKE CONNECT ... FROM PUBLIC` 且幂等（不重建、不改密码）。
- 内部接口（agent → api，`X-Internal-Token`，请求/响应模型以 `apps/api/app/api/schemas/internal.py` 为唯一权威）：

| 方法 | 路径 | 请求 | 响应 |
|---|---|---|---|
| POST | `/internal/sessions/ensure` | `{thread_id}` | `{game_id, sandbox_id, created}` |
| POST | `/internal/db/provision` | `{thread_id}` | `{game_id, database_url}` |
| POST | `/internal/games/publish` | `{thread_id, name}` | `{game_id, public_url, seq}` |

- 常量集中：`apps/api/app/core/constants.py`、`apps/agent/agent/core/constants.py`。

## 规则

- 配置全读环境变量，禁写死，无默认值，缺失 fail-fast；本地唯一配置源为 `apps/.env`（不提交）。
- **唯一配置样板为 `apps/.env.example`**（全部变量清单；服务器部署照抄后按文件头的「服务器需改 16 项」改值）。
- Python：`apps/api`、`apps/agent` 各自独立 `uv` + `uv.lock`；`.python-version` 均为 `3.14.4`，`requires-python >=3.14,<3.15` 保持一致；不使用 uv workspace。
- Node：`sandbox/game-template` 使用 npm，`package-lock.json` 必须提交。
- 同步模式：api 路由用 `def` + 同步 `Session`，不引入 async SQLAlchemy。
- 分层依赖方向：`api → services → repositories → models`，`gateways`/`core` 可被任意层引用；业务错误用 `app/core/exceptions.py` 的异常类，由全局 handler 映射，禁止路由写 try/except 错误映射。
- 删除文件用 `trash`，不用 `rm`；文档/注释/错误信息用中文。
- 测试：`make test`（= `cd apps/api && uv run pytest`），用例在 `apps/api/tests/`，跑在独立库 `aigame_platform_test`（自动建/删）；**任何测试都不得指向开发库 `aigame_platform`**（conftest 有硬性护栏）。