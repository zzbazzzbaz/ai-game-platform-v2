# legacy —— 旧实现冻结参考

本目录是旧项目 `2026.9/AI游戏平台/services` 的**只读快照**（2026-09-28 版本），技术栈为
Modal 沙盒 + MinIO + 自研快照 + 单文件发布，已被 10.8 规格（A1）取代。

## 规则

- **禁止 import / 复制进正式代码**（规格：正式项目不引用旧项目代码）。
- 仅作为过渡期参考（如 `api_server` 的分层写法、`agent_server` 的 deepagents 接入方式）。
- **M6 打通后删除本目录**。

## 快照与现状的对应

| 旧（legacy/services） | 新 |
|---|---|
| `api_server`（FastAPI 骨架、分层规范） | `apps/api`（已重写） |
| `agent_server`（deepagents + ModalBackend） | `apps/agent`（AgsBackend + JWKS 验签） |
| `sandbox`（Modal 镜像 + Phaser skills） | `sandbox/`（skills + init.sh + 发布脚本）与 `sandbox/game-template/` |
| `deploy`（compose） | 根 `docker-compose.yml`（本地平台 PG） |
