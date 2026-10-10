# AI 游戏平台（v0.2 · 规格 A1）

面向无编程基础用户：与 AI 多轮对话生成「带服务端的可玩游戏」，沙盒内实时预览，一键发布公网。

- 唯一架构依据：`docs/spec/技术架构规格.md`（v0.2.1）
- 操作细节与坑：`docs/chat/10.8/02-技术架构规格.md`、`docs/chat/10.8/03-验证结论与坑.md`
- 本仓库处于**开发阶段**：只做本地开发，不涉及生产部署。

## 仓库结构

| 路径 | 内容 | 性质 |
|---|---|---|
| `apps/api/` | FastAPI 平台后端；唯一持云凭证与 PG 管理凭证；认证签发方 | Python 工程（uv） |
| `apps/agent/` | LangGraph Server + deepagents；只持沙盒访问权（E2B Key）与内部令牌 | Python 工程（uv） |
| `sandbox/` | 沙盒资产 + 游戏模板：`game-template/`（npm 工程）、`init.sh`、`assets/skills/`、`publish_assets.py` | 子目录为 npm 工程，其余为脚本/资产 |
| `legacy/` | 旧实现冻结参考；**禁止 import**；M6 打通后删除 | 冻结代码 |
| `docs/` | 规格与讨论记录（`docs/db/` 为数据库说明） | 文档 |

前端（apps/web）暂缓，等 M5/M6 打通后再做。

## 开发环境拓扑（本阶段）

- **平台元数据库**（`users` / `games` / `game_threads` / `game_versions`）：**本地 Docker PG**（`docker-compose.yml`，`aigame_platform`）。
- **游戏数据库**（每游戏 `game_{sid}` + role `game_{sid}_rw`）：**公网 VPS PG**（`152.32.215.89:10050`，由 api 管理员凭证开通；沙盒经公网直连）。
- AGS 沙盒、COS 桶均为腾讯云端资源（本地开发同样使用）。

## 跨服务契约（改动必须同步）

- 命名根：`game_id`（UUID）；`sid = game_id 去掉"-"`（32 位十六进制）；所有外部资源命名只由 game_id 推导。
- 沙盒（AGS `aio` 预置）：`metadata.game_id = game_id`；工作区 `/workspace/work`（COS `games/{game_id}/`）、素材 `/workspace/input`（只读）、依赖 `/opt/deps`、skills `/opt/skills`。
- COS 前缀：游戏资产 `games/{game_id}/**`；版本包 `games/{game_id}/versions/{seq}.tar`；平台资产 `platform/**`。
- 托管服务名：`g-{sid}`（云托管服务名上限 36 字符，`game-{game_id}` 超限；仍仅由 game_id 派生）。
- 游戏数据库：`game_{sid}`、role `game_{sid}_rw`，密码 = `base64url(HMAC-SHA256(GAME_DB_PASSWORD_MASTER_SECRET, game_id))`；开通必须 `REVOKE CONNECT ... FROM PUBLIC` 且幂等（不重建、不改密码）。
- 内部接口（agent → api，`X-Internal-Token`，请求/响应模型以 `apps/api/app/api/schemas/internal.py` 为唯一权威）：

| 方法 | 路径 | 请求 | 响应 |
|---|---|---|---|
| POST | `/internal/sessions/ensure` | `{thread_id}` | `{game_id, sandbox_id, created}` |
| POST | `/internal/db/provision` | `{thread_id}` | `{game_id, database_url}` |
| POST | `/internal/sessions/{thread_id}/server/restart` | — | `{ok, log_tail}` |
| POST | `/internal/games/publish` | `{thread_id, name}` | `{game_id, public_url, seq}` |

- 常量集中：`apps/api/app/core/constants.py`、`apps/agent/agent/core/constants.py`。

## 规则

- 配置全读环境变量，禁写死，无默认值，缺失 fail-fast；本地唯一配置源为根 `.env`（不提交），样板见 `.env.example`。
- Python：`apps/api`、`apps/agent` 各自独立 `uv` + `uv.lock`；`.python-version` 均为 `3.14.4`，`requires-python >=3.14,<3.15` 保持一致；不使用 uv workspace。
- Node：`sandbox/game-template` 使用 npm，`package-lock.json` 必须提交。
- 同步模式：api 路由用 `def` + 同步 `Session`，不引入 async SQLAlchemy。
- 分层依赖方向：`api → services → repositories → models`，`gateways`/`core` 可被任意层引用；业务错误用 `app/core/exceptions.py` 的异常类，由全局 handler 映射，禁止路由写 try/except 错误映射。
- 删除文件用 `trash`，不用 `rm`；文档/注释/错误信息用中文。

## 安全底线（规格 §10）

- 管理员凭证只在 `apps/api`；agent / 沙盒 / 游戏服务不持有云端管理凭证。
- 游戏代码视为不可信：只读平台注入的环境变量（`DATABASE_URL` / `PORT`）。
- NoVNC 令牌与云凭证不得进入游戏产物；`env.md` / `.env` / `.keys` 不得提交。
- 沙盒内访问 COS 挂载点必须以 `user="root"` 执行；`node_modules` 不进挂载层。

## 常用命令

```bash
make up            # 本地平台 PG
make jwt-keys      # 生成开发用 RS256 密钥（apps/api/.keys/）
make install       # 同步 api/agent/模板依赖
make run-api       # 启动 api（8000）
make run-agent     # 启动 agent（2024，langgraph dev）
make sandbox-assets-publish   # 发布模板/skills/init.sh 到 COS platform/ 前缀
```
