# 01 · AGS 依赖包与 COS 挂载调研

> 日期：2026-10-09 ｜ 范围：腾讯云 Agent Runtime / Agent 沙箱（AGS）在本项目（deepagents / LangGraph → E2B 协议 → AGS）下的接入方式
> 方法：腾讯云官方文档 + E2B 官方文档 + PyPI 实时版本核对，与 `docs/chat/10.8/03-验证结论与坑.md` 的实测结论交叉验证

## TL;DR（两个问题的答案）

1. **依赖包**：分层看——
   - 数据面（沙盒内操作）：**E2B 官方 SDK**（`e2b`；代码解释器场景用 `e2b-code-interpreter`）。腾讯**没有自研数据面包**，官方快速入门就是让你 `pip install e2b-code-interpreter` / `from e2b import Sandbox`。
   - Agent 集成（本项目）：**`langchain-e2b` + `deepagents` + `e2b`**。`langchain-e2b` 是 E2B 官方出的 Deep Agents 沙盒后端适配器，负责把"已创建的 e2b 沙盒"包成 deepagents 的工具执行环境；**生命周期（create/kill）仍由 `e2b` SDK 自己管**。
   - 控制面（建工具 / 挂载 / 实例管理）：腾讯官方 **`agr` CLI** 或 **`tencentcloud-sdk-python-ags`**（无 e2b 对应能力）。
2. **AGS 挂 COS**：**腾讯 AGS 私有功能**，不是标准 E2B。腾讯文档原话："E2B 原生不支持 MountOptions 字段，AGS 可以支持 E2B SDK 通过 `metadata["x-mounts"]` 传递 JSON 格式的挂载配置"。它借用了标准 E2B SDK 的 `metadata` 透传位，所以从代码上看"无缝"，但语义是 AGS 私有约定。

---

## 1. 依赖包：分三层

| 层 | 干什么 | 推荐包 | 来源 |
|---|---|---|---|
| 数据面（沙盒内） | 创建/销毁沙盒、执行命令、读写文件、NoVNC/CDP 取址 | `e2b`（Python ≥2.x）；代码解释器场景 `e2b-code-interpreter` | E2B 官方；腾讯官方推荐接入方式 |
| Agent 集成 | deepagents 内置文件/终端工具跑在沙盒里 | `langchain-e2b` + `deepagents` + `e2b` | E2B 官方适配器（非腾讯、非 LangChain 自研） |
| 控制面（管理） | 建/查沙箱工具（含 StorageMounts）、启停实例、挂载覆盖、API Key | `agr` CLI；`tencentcloud-sdk-python-ags`（或全量 `tencentcloud-sdk-python`） | 腾讯官方自研（Python/Go SDK、CLI、MCP、REST API） |

### 1.1 官方依据（原文摘录）

- **AGS 快速入门**（[1814/123816](https://cloud.tencent.com/document/product/1814/123816)）：
  - 场景一"接入 Agent Sandbox"：`uv pip install e2b-code-interpreter`；`E2B_DOMAIN="ap-guangzhou.tencentags.com"`；`E2B_API_KEY="e2b_xxxx"`（控制台创建）；`Sandbox.create(template="code-interpreter-v1", timeout=3600)`；`sandbox.run_code(...)`。
  - 场景二"迁移场景，兼容 E2B"：**沙箱工具名与 E2B 模板名（template）保持一致，只改 `E2B_DOMAIN` / `E2B_API_KEY` 两个环境变量**，E2B 侧代码原样可用。
- **产品动态**（[1814/123809](https://cloud.tencent.com/document/product/1814/123809)）：2026-06-01 "E2B SDK 兼容公有云 API Key……便于使用 E2B SDK 接入 AGS"。
- **产品简介 PDF**：接入方式 = "SDK（Python、Go）、CLI、MCP、RESTful API……**兼容 E2B 等社区主流开源沙箱协议**"；文件操作 = "支持外挂 COS 对象存储、CFS 高性能文件存储"。
- **本项目已验证**：`e2b` 2.52.0 + `E2B_DOMAIN=ap-shanghai.tencentags.com`，`Sandbox.create/list/connect`、`commands.run`、`files.write`、`get_host`、CDP 全部可用（见《03-验证结论与坑》§1）。

### 1.2 版本现状（2026-10-09，PyPI 实测）

| 包 | 最新 | 依赖约束 / 备注 |
|---|---|---|
| `e2b` | 2.55.0 | 项目验证基线为 **2.52.0**，建议 pin `~=2.52.0` 保证可复现 |
| `e2b-code-interpreter` | 2.10.3 | 要求 `e2b>=2.53.0`（比验证基线新，注意） |
| `langchain-e2b` | 0.0.6 | 要求 `deepagents>=0.6.0,<0.7.0`、`e2b>=2.32,<3` |
| `deepagents` | 0.7.23 | ⚠️ 与 langchain-e2b 0.0.6 的 `deepagents<0.7` 上限**冲突**（见 1.4） |
| `tencentcloud-sdk-python-ags` | 3.1.183 | AGS 控制面 SDK（云 API 版本 2025-09-20） |
| `agr`（AGS CLI） | 验证时 v0.6.7 | `brew install TencentCloudAgentRuntime/tap/agr-cli`，或 `curl -fsSL https://dl.tencentags.com/agr-cli/latest/install.sh \| sh` |

### 1.3 建议的依赖组合

```bash
# 在 AGS+COS学习/ 下（pyproject.toml 已存在，可用 uv add 填充）
uv add "e2b~=2.52.0"                # 数据面（与验证基线一致）
uv add "playwright>=1.40"          # CDP 自检 / 截图（可选，验证脚本用）

# 若接入 deepagents 内置沙盒工具（注意 deepagents 版本上限，见下）：
uv add "deepagents~=0.6.0" "langchain-e2b==0.0.6"

# 控制面（可选，平台自动建 Tool / 查实例时用）：
uv add tencentcloud-sdk-python-ags
```

> `langchain-e2b` 只在"使用 deepagents 内置文件/终端工具"时才需要。项目《02》§6.4 的自定义工具（`provision_database` / `restart_server` / `screenshot` / `publish_game`）本来就直连 `e2b` SDK，不依赖它。

### 1.4 ⚠️ deepagents 版本冲突（当前实际状态）

`langchain-e2b 0.0.6`（最新，2026-07-24 发布）锁定 `deepagents<0.7.0`，而 `deepagents` 最新已到 **0.7.23**（2026-10-07）。三条路选一：

1. **Agent 侧暂用 `deepagents==0.6.x` + `langchain-e2b`**（最省事，等适配器更新）；
2. **只用 `e2b` + 自写薄适配器**：继承 `deepagents.backends.sandbox.BaseSandbox`，只需实现 `execute`（内部 `commands.run`）与文件上传/下载（`files.write/read`）——可参考 langchain-e2b 源码（`langchain_e2b/sandbox.py`），工作量很小，且能自行规避版本约束；
3. **不用 sandbox backend**：deepagents 内置文件/终端工具不用，全部自定义工具走 `e2b`。

> langchain-e2b 对 e2b SDK 的实际调用面（读其源码确认）：`commands.run`、`files.read` / `files.write` / `files.get_info`（含 AsyncSandbox 异步版）。这些都在 AGS 已验证或官方文档支持的范围内，但建议上线前做一轮冒烟（见 §3）。

### 1.5 不要用什么

- **`langchain-community` 里的旧 E2B 工具**（如 `E2BDataAnalysisTool`）：面向旧版 E2B / Code Interpreter 数据分析路线，与本项目"通用沙盒 + 浏览器 + 文件/命令"不符，勿混用。
- **不存在"腾讯官方 e2b 分叉包"**：数据面就是 E2B 官方包 + AGS 域名；腾讯官方的 Python 包只有控制面的 `tencentcloud-sdk-python-ags`。

---

## 2. AGS 挂 COS：私有功能，但"穿着标准协议的外衣"

### 2.1 官方原话（关键证据）

腾讯云 AGS 文档《挂载文件系统 CFS》（[1814/129845](https://cloud.tencent.com/document/product/1814/129845)）：

> "E2B 原生不支持 MountOptions 字段，AGS 可以支持 E2B SDK 通过 `metadata["x-mounts"]` 传递 JSON 格式的挂载配置"

AGS 文档《存储挂载》（[1814/132215](https://cloud.tencent.com/document/product/1814/132215)）定义了完整的两层配置模型（存储来源：COS / CFS / 镜像）。

**结论**：`StorageMounts` / `MountOptions` / `x-mounts` 都不是 E2B 生态概念，E2B 官方 SDK 与文档中不存在。这是 AGS 私有扩展，寄生在标准 E2B SDK 的 `Sandbox.create(metadata=...)` 透传字段上——属于"利用标准协议的扩展点做私有约定"，不是"标准 E2B 实现"。

### 2.2 AGS 挂载模型（官方两层）

| 层 | 配置 | 谁配置 | 作用 |
|---|---|---|---|
| Tool 级 | `StorageMounts`（COS / CFS / Image） | 控制台 / `agr tool create --storage-mounts` / `CreateSandboxTool` | 定义默认来源、默认挂载路径、读写权限 |
| Instance 级 | `MountOptions`（腾讯 SDK/CLI）／`metadata["x-mounts"]`（E2B SDK，camelCase） | `agr instance create --mount-options` / `StartSandboxInstance` / `Sandbox.create(metadata=...)` | 引用 Tool 中的 `Name`；可覆写 `MountPath`、只读收紧、追加 `SubPath` 做实例级目录隔离 |

要点（官方规则 + 项目实测）：

- **COS 挂载必填**：`BucketName`、`BucketPath`、`MountPath`、`RoleArn`（CAM 角色，信任主体 `sandboxtool.ags.cloud.tencent.com`）；**不传 `Endpoint`，AGS 按当前地域自动补全**。
- `x-mounts` 字段名**小驼峰**（`name` / `mountPath` / `readOnly` / `subPath`）；腾讯 SDK/CLI 是**大驼峰**（`Name` / `MountPath` / `ReadOnly` / `SubPath`）。
- 实例级 `ReadOnly` **只能收紧，不能放宽**；同 Tool 最多 10 条挂载；`SubPath` 必须相对路径（不能 `..`、`//`）。
- Tool 创建后**不能改 StorageMounts**（CLI 公开字段不含它）→ 调整默认配置需新建 Tool（与《03》§2.3 第 5 条一致）。
- COS `BucketPath` 与实例 `subPath` 目录**必须先存在**（放占位对象）；沙盒内访问挂载点必须 `user="root"`；挂载呈现为 `virtiofs`（《03》§2.3）。

### 2.3 对照：标准 E2B 的持久化是什么

| 能力 | E2B 官方 | AGS |
|---|---|---|
| 生命周期持久化 | `pause/resume`（快照） | 平台侧暂停/恢复；另有 COS/CFS 挂载 |
| 持久卷 | `Volumes`（**private beta**；`Sandbox.create(volume_mounts={...})`，卷由 E2B 托管） | 无此概念（用 AGS StorageMounts 替代） |
| 挂对象存储（COS/S3） | ❌ 无官方能力 | ✅ COS 挂载（需 RoleArn） |
| 实例级子目录隔离 | 自定义挂载路径 | `x-mounts.subPath`（项目用它做"每游戏一个子目录"） |

即：E2B 官方的 `volume_mounts` 与 AGS 的 `x-mounts` **不是一回事，不要混用**（AGS 文档也没有承诺兼容 `volume_mounts`）。

### 2.4 对项目文档的修正建议

- 《02》§6.2 把 `metadata["x-mounts"]` 标注为"标准 E2B 扩展"——**建议改为"AGS 私有扩展"**。行为与约束不变，只是避免后续开发误以为 E2B 官方也有此机制。
- 《03》§7 写 "E2B Python SDK 2.52.0"，而 `附录/sandbox/pyproject.toml` 写 `e2b>=1.0.0`——建议统一 pin 到 `e2b~=2.52.0`（或重新验证 2.5x 最新版后更新文档）。

---

## 3. 建议的动手验证（下一步）

1. **langchain-e2b × AGS 冒烟**：在 AGS 沙盒上跑 `commands.run`、`files.write/read/get_info`（同步 + 异步）——可覆盖 langchain-e2b 的全部依赖面。
2. **deepagents 版本组合**：`deepagents==0.6.x + langchain-e2b==0.0.6` 跑通 `create_deep_agent(backend=E2BSandbox(sandbox=...))`；若必须 0.7.x，评估 §1.4 的第 2/3 条路。
3. **控制面 API 打通**（可选）：用 `agr` / `tencentcloud-sdk-python-ags` 自动创建带 StorageMounts 的 Tool、启动实例并传 `MountOptions`——为"平台自动开通沙盒"做准备（当前项目的 Tool 是控制台手工建的）。

## 4. 参考链接

- AGS 快速入门（E2B 兼容接入）：https://cloud.tencent.com/document/product/1814/123816
- AGS 存储挂载（两层模型，COS/CFS/Image）：https://cloud.tencent.com/document/product/1814/132215
- AGS 挂载 CFS（"E2B 原生不支持 MountOptions"原文 + x-mounts 示例）：https://cloud.tencent.com/document/product/1814/129845
- AGS All-In-One 沙箱操作（9000/49983/49999 端口能力）：https://cloud.tencent.com/document/product/1814/130978
- AGS 产品动态（E2B 兼容 API Key）：https://cloud.tencent.com/document/product/1814/123809
- 启动沙箱实例 API（MountOptions 字段）：https://cloud.tencent.com/document/product/1814/124816
- AGS CLI（`agr`）：https://github.com/TencentCloudAgentRuntime/ags-cli
- E2B × LangChain Deep Agents 官方集成页：https://docs.e2b.dev/agents/deep-agents
- langchain-e2b 仓库：https://github.com/e2b-dev/langchain-e2b
- E2B Volumes（private beta）：https://docs.e2b.dev/volumes
- E2B 沙盒持久化（pause/resume）：https://e2b.dev/docs/sandbox/persistence
- 项目验证基线：`../docs/chat/10.8/03-验证结论与坑.md`
