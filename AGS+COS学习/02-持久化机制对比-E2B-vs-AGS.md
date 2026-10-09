# 02 · 沙盒持久化机制对比：E2B vs 腾讯云 AGS

> 日期：2026-10-09 ｜ 背景：01 笔记确认"AGS 挂 COS 是腾讯私有功能"。本篇回答：那 E2B 自己怎么做沙盒文件持久化？用对象存储吗？AGS 有没有实现同样的方案？

## TL;DR

- **E2B 原生持久化不依赖"用户可见的对象存储"**：核心是 **pause/resume 快照**（默认文件系统 + 内存；可只存文件系统），另有 **Snapshots（一对多克隆）** 和 **Volumes（private beta，E2B 托管卷）**。存储由 E2B 平台内部管理，用户接触不到，也不能挂自己的 S3/GCS。
- E2B 官方对"挂对象存储"的态度是 **DIY**：自定义模板装 FUSE（`gcsfuse` / `s3fs`），运行时手动 mount；或接第三方 Archil。**E2B 没有平台托管的对象存储挂载能力**。
- **腾讯 AGS 两套都有**：
  1. 实现了 E2B 式的**暂停/恢复**：`PauseSandboxInstance` / `ResumeSandboxInstance`（CLI `agr instance pause/resume`），产品文档称"进程级快照完整保留运行上下文，暂停时释放资源、按需快速恢复"；项目组此前也用 e2b SDK 标准 `pause/resume` 实测可用（见《03》§2，最终未采用）。
  2. 在此之上**自研了 COS/CFS 托管挂载**（E2B 没有的能力），即项目现在用的方案。
- 注意 AGS 语境里的"**沙箱快照**"指平台内部**预热用的初始化快照**（用于秒级启动），不是用户可以创建/克隆的 API。

## 1. E2B 的持久化方案（官方）

| 机制 | 操作 | 保留内容 | 关键语义 |
|---|---|---|---|
| **Pause / Resume**（核心） | `sbx.pause()` → 之后 `Sandbox.connect()` 恢复 | 默认**文件系统 + 内存**（运行进程、变量都恢复）；`keep_memory=False` 只存文件系统，恢复时重启（进程丢失） | **暂停的沙盒无限期保留、不自动删除**；pause 约 4s/GiB RAM，resume 约 1s；恢复后客户端连接（WS/PTY/命令流）需重连 |
| **Snapshots**（时间点快照，一对多） | `sandbox.create_snapshot()`；用快照 `Sandbox.create()` 派多个新沙盒 | 文件系统 + 内存（可 `mode="filesystem"`） | 原沙盒继续运行；一个快照可克隆多个沙盒；需 envd ≥ v0.5.0 |
| **Forking** | 一次调用完成"快照 + 批量起新沙盒" | 同上 | 用于并行探索/分支 |
| **Volumes**（private beta） | `Sandbox.create(volume_mounts={...})` | 独立于沙盒生命周期的持久卷 | 卷由 **E2B SDK/平台管理**，可多沙盒共享；不是用户的对象存储 |
| Auto-pause / auto-resume | 超时自动暂停、访问时自动恢复 | 同上 | 可配置为 filesystem-only |

**存储在哪？** 以上快照/卷的底层存储由 E2B 托管（其自研 Firecracker 快照体系），用户不接触、不可替换；**E2B 不提供"挂你的 S3/GCS/COS"的平台功能**。

## 2. E2B 想用对象存储怎么办？（官方 DIY 路线）

- 官方文档 **Cloud buckets**：在**自定义模板**里装 `gcsfuse`（GCS）/ `s3fs`（S3），沙盒运行时用命令手动 `mount` 桶到目录（FUSE）。权限、挂载生命周期、路径隔离全部自己处理。
- 第三方 **Archil**：把 S3 / R2 / GCS 转成高性能 POSIX 文件系统挂进 E2B 沙盒。
- 也就是说：在 E2B 生态里，"对象存储挂载"是用户自建能力，不是平台能力。

## 3. 腾讯云 AGS 的对应实现

| E2B 能力 | AGS 对应 | 证据 |
|---|---|---|
| pause / resume | ✅ `PauseSandboxInstance` / `ResumeSandboxInstance`；控制台与 `agr instance pause/resume` 均可；"进程级快照完整保留运行上下文，暂停时释放资源、按需快速恢复" | [API 概览 124833](https://cloud.tencent.com/document/product/1814/124833)、[产品优势 123813](https://cloud.tencent.com/document/product/1814/123813) |
| snapshot / fork（一对多克隆） | ❌ 未见公开 API；AGS 的"沙箱快照"是**内部预热机制**："默认提供 code/浏览器沙箱的初始化沙箱快照，实现资源预热，快速启动" | [基本概念 123814](https://cloud.tencent.com/document/product/1814/123814) |
| volumes | ❌ 无卷概念；用 COS/CFS 挂载替代 | [存储挂载 132215](https://cloud.tencent.com/document/product/1814/132215) |
| 挂对象存储 | ✅ **AGS 自研托管挂载**：COS/CFS，RoleArn 授权、Tool 级 `StorageMounts`、实例级 `MountOptions` / `x-mounts`、`subPath` 隔离、Endpoint 自动补全 | 存储挂载 132215；01 笔记 |

> 补充：项目《03》§2 明确记录了"备选方案（已验证但不采用）：标准 E2B `pause/resume` + 平台侧打包同步到 COS"——即 AGS 的暂停/恢复在 e2b 兼容层是通的，只是当年选择了 COS 挂载路线。

### 3.1 一对一对照：E2B Volumes ↔ AGS COS/CFS 挂载

> 一种常见概括："腾讯用 COS/CFS 挂载替代了 E2B 的 Volumes 产品"。功能对标上成立，但两者的**托管模型**完全不同。更精确的表述：**AGS 用"挂载自有云存储"的路线，实现了 E2B Volumes 同类的"跨沙盒生命周期持久化挂载"能力。**

| 维度 | E2B Volumes | AGS COS/CFS 挂载 |
|---|---|---|
| 存储归属 | **E2B 平台托管**（黑盒；数据只在 E2B 生态内） | **BYO 存储**：你自己的 COS 桶 / CFS 文件系统 |
| 生命周期管理 | 卷由 E2B SDK 管理（create / connect / list / inspect / destroy） | 挂载由 AGS 管理；COS 桶 / CFS 文件系统各自按云产品管理 |
| 挂载配置 | `Sandbox.create(volume_mounts={...})`（创建时） | Tool 级 `StorageMounts`（默认来源）+ 实例级 `MountOptions` / `x-mounts`（覆盖路径、收紧只读、`subPath` 隔离） |
| 多沙盒共享 / 隔离 | 同一卷可挂载到多个沙盒 | 同一桶可共享；`subPath` 实现实例级隔离 |
| 外部系统访问 | 需经 E2B SDK 导出 | ✅ 平台后端 / 其它系统可直接读写（版本打包、素材管理） |
| 性能形态 | E2B 托管（黑盒） | COS（virtiofs，小文件慢）/ CFS（POSIX，共享目录场景） |
| 计费 | E2B 计费 | COS / CFS 独立计费 |
| 成熟度 | **private beta** | 正式文档化能力 |
| 其它存储来源 | — | 还支持 **Image 只读挂载**（预置脚本 / 依赖基线） |
| 授权 | E2B API Key | CAM `RoleArn`（信任主体 `sandboxtool.ags.cloud.tencent.com`） |

另外两点值得记住：

- AGS 的 COS 挂载其实同时覆盖了 E2B 的**另一条 DIY 路线**（Cloud buckets：自己装 FUSE 挂 S3/GCS）——AGS 把"挂自己的对象存储"升级成了平台托管功能。
- "替代 Volumes"只是持久化版图的一半：E2B 还有 pause/snapshot 体系，AGS 也已实现 pause/resume（见上表 §3）。


## 4. 两种路线怎么选（对本项目的结论）

| 维度 | pause/resume（E2B 式） | COS 挂载（AGS 式，项目现选） |
|---|---|---|
| 保留什么 | 沙盒**状态**（可选含内存/进程），恢复还是"同一个沙盒" | 文件**实时落 COS**（对象存储），沙盒只是访问入口 |
| 平台后端直接读工作区 | ❌ 需经沙盒导出/接口 | ✅ 直接读 COS（版本打包、素材上传） |
| 换镜像/规格/重建后恢复 | 需恢复同一沙盒快照 | 任意新沙盒挂同一 subPath 即得 |
| 隔离粒度 | 实例 | `subPath` 子目录 → 每游戏/每会话隔离 |
| 性能注意 | resume 快（1s 级）；pause 约 4s/GiB | 大量小文件慢（`node_modules` 不放挂载层）；virtiofs |
| 生命周期/配额 | E2B：暂停无限期保留；AGS：见官方配额页（待确认） | COS 按存储/请求计费 |

**组合建议**：
- 工作区持久化继续用 **COS 挂载**（现状正确）：满足"平台侧可读 + 每游戏隔离 + 沙盒随意销毁重建"。
- 若后续追求开发会话"秒级保活"，可叠加 **pause/resume** 作加速手段；按项目 R-SBX-5 用 `keep_memory=False`（文件系统级），内存级支持度建议实测后再启用。

## 5. 待确认清单

- AGS `PauseSandboxInstance` 的保留时长、计费与配额（E2B 是"暂停无限期保留"，AGS 以其配额页为准）。
- e2b SDK `pause()/connect()` 在 AGS 上 `keep_memory=True/False` 的行为差异（项目规定 False）。
- AGS 是否会把 snapshot / fork 能力开放为公开 API（目前没有）。

## 参考链接

- E2B 持久化（pause/resume）：https://docs.e2b.dev/sandbox/persistence
- E2B 仅文件系统快照：https://docs.e2b.dev/sandbox/filesystem-only-snapshots
- E2B Snapshots：https://docs.e2b.dev/sandbox/snapshots ｜ Fork：https://docs.e2b.dev/sandbox/fork
- E2B Volumes（private beta）：https://docs.e2b.dev/volumes
- E2B Cloud buckets（DIY FUSE 挂桶）：https://docs.e2b.dev/storage/cloud-buckets ｜ Archil：https://docs.e2b.dev/storage/archil
- AGS API 概览（Pause/ResumeSandboxInstance）：https://cloud.tencent.com/document/product/1814/124833
- AGS 产品优势（进程级快照）：https://cloud.tencent.com/document/product/1814/123813
- AGS 基本概念（沙箱快照=预热初始化快照）：https://cloud.tencent.com/document/product/1814/123814
- AGS 存储挂载（COS/CFS）：https://cloud.tencent.com/document/product/1814/132215
- 项目验证基线：`../docs/chat/10.8/03-验证结论与坑.md`
