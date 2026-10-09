# AI 游戏平台

用自然语言与 AI 多轮对话生成「带服务端的可玩游戏」，沙盒内实时预览，一键发布公网。

- 架构规格（唯一依据）：`docs/spec/技术架构规格.md`
- 交接文档集（含验证结论与坑）：`docs/chat/10.8/`
- 工程约定与目录说明：`AGENTS.md`

## 快速开始（开发）

```bash
cp .env.example .env      # 填好密钥（VPS PG、E2B、COS、LLM）
make up                   # 本地平台 PG
make jwt-keys             # 开发用 RS256 密钥
make install              # 同步 Python / Node 依赖
make run-api              # http://127.0.0.1:8000
make run-agent            # http://127.0.0.1:2024
```
