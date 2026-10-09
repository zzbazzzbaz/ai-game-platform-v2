# app —— api_server 应用根

先应用 services/AGENTS.md，再应用本文件。

## 分层与依赖方向

- 依赖方向自上而下，禁止反向 import：`api → services → repositories → models`；`gateways` 与 `core` 可被任意层引用。
- `core/`：框架无关（config/database/security/exceptions/constants）。
- `repositories/`：DB 查询入口，services 不直接写 `select`/`session.get`。
- `gateways/`：外部适配器（MinIO/Modal），负责把 SDK 异常翻译成 `UpstreamError`。
- `services/`：业务编排，入参用原始类型/dict，外部资源（session/modal/minio）由调用方传入。

## 约束（MUST NOT）

- 业务错误禁用内建 `ValueError`/`PermissionError`/`RuntimeError`，必须用 `core/exceptions.py` 的 `ValidationError`(400)/`ForbiddenError`(403)/`NotFoundError`(404)/`UpstreamError`(502)；内建异常会绕过全局 handler 变 500。
- `core/` 禁止 import FastAPI 或上层包；异常到 HTTP 的映射只准出现在 `api/errors.py`。
- services/repositories 禁止自行构造外部客户端（MinioGateway/ModalGateway/engine），一律走依赖注入。

## 约定

- 已锁定决策（不要再翻案）：
  - 同步模式：路由用 `def`、同步 `Session`，不引入 async/AsyncSession。
  - DTO 归属 `api/schemas/`，不用 `app/schemas/`。
  - 自定义异常 + `api/errors.py` 全局 handler，路由不做 try/except 错误映射。
  - 常量全部集中 `core/constants.py`（路径/分块/沙箱/版本/正则/媒体类型/大小限制），业务模块禁止新增模块级常量（运行期对象如下划线开头的锁/元组除外）。
- 错误 `detail` 用中文。
- 新增 DB 访问先加 repository 方法，再由 service 调用。