# AI 游戏平台（v0.2 · 规格 A1）

面向无编程基础用户：与 AI 多轮对话生成「带服务端的可玩游戏」，沙盒内实时预览，一键发布公网。

## 仓库结构

| 路径 | 内容 | 性质 |
|---|---|---|
| `apps/api/` | FastAPI 平台后端；唯一持云凭证与 PG 管理凭证；认证签发方 | Python 工程（uv） |
| `apps/agent/` | LangGraph Server + deepagents；只持沙盒访问权（E2B Key）与内部令牌 | Python 工程（uv） |
| `sandbox/` | 沙盒资产：`image/`（AGS 自定义镜像 Dockerfile + 启动脚本）、`game-template/`（游戏工程模板）、`assets/skills/`（Phaser 技能库） | 镜像/资产 |
| `docs/` | 规格与讨论记录（`docs/db/` 为数据库说明） | 文档 |

## 开发环境拓扑（本阶段）

- **平台元数据库**（`users` / `games` / `game_threads` / `game_versions`）：**本地 Docker PG**（`apps/docker-compose.yml`，`aigame_platform`）。
- **游戏数据库**（每游戏 `game_{sid}` + role `game_{sid}_rw`）：**公网 VPS PG**（`152.32.215.89:10050`，由 api 管理员凭证开通；沙盒经公网直连）。
- AGS 沙盒、COS 桶均为腾讯云端资源（本地开发同样使用）。

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

- 配置全读环境变量，禁写死，无默认值，缺失 fail-fast；本地唯一配置源为 `apps/.env`（不提交），样板见 `apps/.env.example`。
- Python：`apps/api`、`apps/agent` 各自独立 `uv` + `uv.lock`；`.python-version` 均为 `3.14.4`，`requires-python >=3.14,<3.15` 保持一致；不使用 uv workspace。
- Node：`sandbox/game-template` 使用 npm，`package-lock.json` 必须提交。
- 同步模式：api 路由用 `def` + 同步 `Session`，不引入 async SQLAlchemy。
- 分层依赖方向：`api → services → repositories → models`，`gateways`/`core` 可被任意层引用；业务错误用 `app/core/exceptions.py` 的异常类，由全局 handler 映射，禁止路由写 try/except 错误映射。
- 删除文件用 `trash`，不用 `rm`；文档/注释/错误信息用中文。