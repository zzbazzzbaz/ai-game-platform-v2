# api —— HTTP 接口层

先应用 `app/AGENTS.md`，再应用本文件。

FastAPI 路由 + 依赖注入 + Pydantic DTO + 异常到 HTTP 的映射。只负责接参、鉴权、错误码；业务逻辑全在 `app/services/`。

## 关键文件

- `dependencies.py`：全部 DI 依赖（`SessionDep`/`AgsDep`/`CosDep`/`PgAdminDep`/`TcbDep`/`UserIdDep`/`InternalDep`），从 `request.app.state` 取全局资源。
- `errors.py`：`AppError` → `{"detail": ...}` 全局 handler。
- `schemas/`：请求/响应模型（HTTP DTO），服务层不 import；`schemas/internal.py` 为内部接口唯一权威。
- `v1/router.py`：聚合各 endpoints，由 main 以 `/api/v1` 前缀挂载；`v1/endpoints/wellknown.py` 由 main 单独挂根路径 JWKS（不经 `/api/v1` 前缀，公开端点）。
- `v1/endpoints/`：按业务域拆文件——`auth`（注册/登录/刷新）、`games`（游戏/会话/版本/玩法图）、`sessions`（预览/沙盒续期）、`internal`（服务间回调）。

## 约束（MUST NOT）

- 路由层禁写业务逻辑，一律调 `app.services.*`。
- 禁再引入 try/except 错误映射样板：service 抛 `AppError` 子类，由 `errors.py` 统一转 HTTP。
- 禁在路由 raise 内建异常表示业务错误；`HTTPException` 仅用于鉴权守卫。
- `internal` 前缀只留给服务间回调（校验 `X-Internal-Token`），禁止混入浏览器/公开接口。

## 约定

- 新增依赖统一加进 `dependencies.py` 并暴露 `XxxDep` 别名，不散落 `Depends()`。
- 端点必须声明 `response_model`（流式/文件响应除外）。
- 错误 `detail` 用中文；需登录的接口用 `UserIdDep`。
