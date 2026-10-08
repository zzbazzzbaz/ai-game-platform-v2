# test/ — 技术路线验证

本目录只用于**验证技术路线**，不是正式项目结构。正式开发以 `docs/spec/技术架构规格.md` 为准。

| 目录 / 文档 | 用途 |
|---|---|
| `infra/sandbox/` | M1 / M4b 验证脚本（AGS / E2B 兼容） |
| `infra/cloudbase/` | M6b 验证（后端 Python SDK 部署云托管 + 探针工程） |
| `M1-沙盒链路验证结论.md` | M1 结论：沙盒 / 浏览器 / CDP / NoVNC |
| `M2-持久化验证结论.md` | M2 结论：AGS 原生 COS 存储挂载 |
| `M3-认证验证结论.md` | M3 结论：JWT **RS256 + 公开 JWKS**（`/auth/v1/certs`）本地验签（调研存档） |
| `M4-数据库验证结论.md` | M4 结论：沙盒**不能直连 PG**；用 **PostgREST + JWT + RLS**；**无法建 role**（调研存档） |
| `M4b-VPS-PG验证结论.md` | M4b 结论：自建 VPS PG 建库/建角色/隔离 + 沙盒公网直连（⚠️ 未启用 SSL） |
| `M6-发布验证结论.md` | M6 结论：CloudRun **支持 WebSocket**；经**公网 PostgREST** 访问库（调研存档） |
| `M6b-API部署与连库验证结论.md` | M6b 结论：后端调 API 部署云托管 + 服务直连 VPS PG |

验证脚本会加载 `*.env`（已被 git 忽略），产物写入各自的 `artifacts/`。
