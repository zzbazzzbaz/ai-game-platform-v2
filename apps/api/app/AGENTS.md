# app —— api 应用根

先应用仓库根 `AGENTS.md`，再应用本文件。

## 分层与依赖方向

- 依赖方向自上而下，禁止反向 import：`api → services → repositories → models`；`gateways` 与 `core` 可被任意层引用。
- `core/`：框架无关（config/database/security/exceptions/constants/naming）。
- `repositories/`：DB 查询入口，services 不直接写 `select`/`session.get`。
- `gateways/`：外部适配器（AGS/COS/PG 管理/TCB），负责把 SDK 异常翻译成 `UpstreamError`。
- `services/`：业务编排；外部资源（session/gateways）由调用方传入。

## 约束（MUST NOT）

- 业务错误禁用内建 `ValueError`/`PermissionError`/`RuntimeError`，必须用 `core/exceptions.py` 的 `ValidationError`(400)/`ForbiddenError`(403)/`NotFoundError`(404)/`UpstreamError`(502)；内建异常会绕过全局 handler 变 500。
- `core/` 禁止 import FastAPI 或上层包；异常到 HTTP 的映射只准出现在 `api/errors.py`。
- services/repositories 禁止自行构造外部客户端（AgsGateway/CosGateway/PgAdminGateway/TcbGateway/engine），一律走依赖注入。
- 常量全部集中 `core/constants.py`；业务模块禁止新增模块级常量。
- 游戏库连接串/口令**禁止落库**；资源命名与口令一律按 `core/naming.py`、`core/security.py` 派生。

## 约定

- 已锁定决策（不要再翻案）：同步模式（路由用 `def`、同步 `Session`，不引入 async SQLAlchemy）；DTO 归属 `api/schemas/`；自定义异常 + `api/errors.py` 全局 handler；错误 `detail` 用中文。
- 新增 DB 访问先加 repository 方法，再由 service 调用。
- 内部接口 `/api/v1/internal/**` 只给 agent：走 `InternalDep`（`X-Internal-Token`），模型以 `api/schemas/internal.py` 为唯一权威。
- 沙盒 ensure（`services/sandbox_service.py`）的并发安全依赖 `game_repository.lock()`：`games` 行锁覆盖「读 sandbox_id → 创建/复用沙盒 → 写 sandbox_id」，同一 game 串行化；COS 前缀/连接串准备与保活命令必须在锁外。回归用例 `tests/test_sandbox_ensure.py::test_concurrent_ensure_creates_single_sandbox`（改动 ensure 必须让它保持通过）。
