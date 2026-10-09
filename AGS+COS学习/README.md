# AGS + COS 学习（工作目录）

> 用途：腾讯云 AGS（Agent 沙箱）与 COS 挂载的调研、笔记与动手验证。
> 背景资料：项目交接文档集 `../docs/chat/10.8/`（`02-技术架构规格.md` / `03-验证结论与坑.md` 为权威依据）。

## 内容索引

| 文件 | 内容 |
|---|---|
| `01-依赖包与COS挂载-调研笔记.md` | ① 依赖包怎么选（e2b / langchain-e2b / 腾讯官方包，含版本现状与坑）；② AGS 挂 COS 是"私有扩展"还是"标准 E2B"（含官方原文证据） |
| `02-持久化机制对比-E2B-vs-AGS.md` | E2B 原生持久化（pause/resume、snapshot/fork、volumes、DIY 挂对象存储）vs AGS 实现（Pause/ResumeSandboxInstance + COS/CFS 托管挂载）；对项目的选型结论 |
| `pyproject.toml` | 占位；动手验证时用 `uv add` 填充（推荐清单见 01 笔记 §1.3） |

## 速览（当前结论）

- 数据面 = **E2B 官方 SDK**（`e2b`，或 `e2b-code-interpreter`），配 `E2B_DOMAIN` + `e2b_` API Key 接入 AGS；腾讯没有自研数据面包。
- Agent 集成 = **`langchain-e2b` + `deepagents`**（注意：langchain-e2b 0.0.6 要求 `deepagents<0.7`，与最新 0.7.x 冲突）。
- 控制面 = 腾讯官方 **`agr` CLI** / **`tencentcloud-sdk-python-ags`**。
- **AGS 挂 COS 是腾讯私有功能**（官方原文："E2B 原生不支持 MountOptions 字段"），通过标准 E2B SDK 的 `metadata["x-mounts"]` 透传实例级挂载参数；Tool 级 `StorageMounts` 只能在控制台/腾讯云 API 配。
- 持久化：E2B 原生 = pause/resume + snapshot/fork + volumes（存储平台托管，不挂你的对象存储，挂桶要 DIY FUSE）；AGS = Pause/ResumeSandboxInstance（已实现）+ COS/CFS 托管挂载（自研增强）。项目用 COS 挂载做工作区持久化是对的（详见 02 笔记）。
