# M6b 验证结论：后端代码调 API 部署到 CloudBase + 连接 VPS PostgreSQL

- 日期：2026-10-08
- 范围：**不使用 MCP / 控制台**，平台后端（Python，腾讯云 SDK）直接调 API：把带服务端的游戏服务部署到 **CloudBase 云托管（CloudRun）**，并通过注入的 `DATABASE_URL` 连接**自建 VPS PostgreSQL**（`152.32.215.89:10050`）
- 结论：**端到端可行** ✅
- 脚本：`test/infra/cloudbase/api_deploy_verify.py`（探针工程：`test/infra/cloudbase/probe-app/`）

## 一、部署流程（与 `@cloudbase/manager-node` 的 `cloudrun.deploy()` 完全一致）

| # | API（产品） | 作用 |
|---|---|---|
| 1 | `tcb:DescribeCloudBaseBuildService` | 返回 `UploadUrl` / `UploadHeaders` / `PackageName` / `PackageVersion` |
| 2 | HTTP `PUT UploadUrl` | 上传源码 zip（本项目 1.0 KB） |
| 3 | `tcbr:CreateCloudRunServer` / `UpdateCloudRunServer` | `DeployInfo={DeployType:"package", PackageName, PackageVersion, ReleaseType:"FULL"}`；`Items` 见下 |
| 4 | `tcbr:DescribeCloudRunServerDetail` | `BaseInfo.DefaultDomainName` / `BaseInfo.Status`；`ServerConfig.EnvParams` 回显注入值；`OnlineVersionInfos` 看镜像 |
| 5 | `tcbr:DescribeCloudRunDeployRecord` | 部署记录（`Status` / `FlowRatio` / `BuildId`） |

`Items`（容器型 + Dockerfile；与 manager-node `parseObjectToDiffConfigItem` 一致）：

```python
[
  {"Key": "AccessTypes", "ArrayValue": ["PUBLIC"]},
  {"Key": "MinNum", "IntValue": 0},
  {"Key": "EnvParam", "Value": json.dumps({"DATABASE_URL": "...", "GAME_ID": "..."})},
  {"Key": "InitialDelaySeconds", "IntValue": 0},
  {"Key": "HasDockerfile", "BoolValue": True},
  {"Key": "Port", "IntValue": 3000},
  {"Key": "Dockerfile", "Value": "Dockerfile"},
]
```

> 平台后端（Python）需要两个 SDK 包：`tencentcloud-sdk-python-tcb` + `tencentcloud-sdk-python-tcbr`（Node 侧则用 `@cloudbase/manager-node`）。

## 二、实测证据

| 项 | 值 |
|---|---|
| 上传 | HTTP **200**（`api-deploy-probe.zip`，version 1791467629） |
| 部署动作 | `UpdateCloudRunServer`（全新则 `CreateCloudRunServer`） |
| 部署记录 | `2026-10-08 21:55:23 status=normal flow=100 buildId=2608325257` |
| 默认域名 | `https://api-deploy-probe-322496-11-1327210567.sh.run.tcloudbase.com` |
| 镜像 | `ccr.ccs.tencentyun.com/tcb-100037354656-bhaj/ca-wlxtdlgz_api-deploy-probe:api-deploy-probe-001-20261008213737` |
| `GET /` | **200** `{"ok":true,"service":"api-deploy-probe","gameId":"game_apideploy_probe"}` |
| `GET /db` | **200** `{"ok":true,"db":"game_apideploy_probe","user":"game_apideploy_probe_rw","version":"PostgreSQL 17.11 …"}` |

- 服务内 `DATABASE_URL` 由 `EnvParam` 注入，指向本游戏库的专属 role（密码派生、不落库）。
- **不需要 VPC**：云托管出公网直达 VPS PG（与 M6 结论一致）。
- 测试资源保留：服务 `api-deploy-probe` + 库/role `game_apideploy_probe(_rw)`（如需删除见 §五）。

## 三、关键坑（实测）

1. **`ResourceInUse`**：上一次部署任务未结束时再调 `UpdateCloudRunServer` → `当前已有部署发布任务运行中,请结束后再执行`。需**等待 + 重试**（本脚本 30s × 12 次）。
2. `DescribeCloudRunServerDetail` 的数据在 `BaseInfo`（`DefaultDomainName`、`Status`）与 `ServerConfig`（`EnvParams` 回显）/`OnlineVersionInfos` 里，**没有**顶层 `DefaultDomainName`（易踩）。
3. **滚动更新窗口**：本次脚本每次重跑都会**重建游戏库并换密码**，滚动更新期间旧实例仍持旧密码 → 短暂 `/db` 500（`password authentication failed for user …`），新版本起来后 200。生产开通必须**幂等**（库/role 已存在则跳过，不换密码），避免无谓重建。
4. 首次部署偶发构建推送失败（`broken pipe` 等）→ 直接重试（沿用 `test/M6-发布验证结论.md`）。
5. 本次部署默认 `OperationMode: alwaysScale`，`MinNum=0`（可由 `Items` 调整）。

## 四、对规格的影响

- §6.7 发布工具：明确"api 侧调**云托管 OpenAPI**（tcb + tcbr）"实现，注入 `DATABASE_URL`；CloudRun 无需 VPC。
- §13 M6 验收：本次覆盖"部署 + 服务访问自身数据库"；剩余"由 Agent 触发发布工具 / 端到端可玩 / WebSocket 新架构复验"待做。
- 与 M4b 联动：数据库连接目前是**明文**（PG 未启用 SSL），见 `test/M4b-VPS-PG验证结论.md`。

## 五、复现 / 清理

```bash
cd test/infra/cloudbase
export TENCENT_SECRET_ID=*** TENCENT_SECRET_KEY=***
export TCB_ENV_ID=test-agent-d5ghby2pe53e38f28 VPS_PG_PASSWORD=***
uv run --with tencentcloud-sdk-python-tcb --with tencentcloud-sdk-python-tcbr \
   --with "psycopg[binary]" --with requests python -u api_deploy_verify.py --keep
```

清理（服务 + 库）：
```bash
# 服务：控制台“云托管”删除，或在脚本中去掉 --keep 运行一次
# 库：DROP DATABASE game_apideploy_probe; DROP ROLE game_apideploy_probe_rw;
```
