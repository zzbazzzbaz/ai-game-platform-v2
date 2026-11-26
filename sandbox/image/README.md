# 沙盒镜像（AGS custom 工具）

单容器提供 agent 工作所需的全部能力，替代 AGS `aio` 预置类型：

| 能力 | 组件 |
|---|---|
| 浏览器 | Xvfb（:0，1280x720）+ x11vnc + noVNC/websockify（**9000**）+ Chromium 应用窗口（自动打开 `http://localhost:3000`） |
| 程序执行 | envd（**49983**，命令/文件接口）+ Node 24 + Python3 + Playwright（Python/Node，Chromium 已装） |
| 工作区 | `/workspace/work`（COS 挂载；为空时 entrypoint 从镜像模板播种）、`/workspace/input`（只读） |
| 预装资产 | 游戏模板及依赖 `/opt/game-template`（`npm ci` 已烘焙，工作区软链 `node_modules`）、技能库 `/opt/skills` |

启动顺序（`image/entrypoint.sh`）：播种工作区 → Xvfb/x11vnc/websockify → 等游戏服务就绪后拉起 Chromium（`image/browser-kiosk.sh`，崩溃自动重启）→ 前台运行 envd。

两个已踩的坑（勿回退）：

- **envd 命令只继承 PATH**，不会带镜像 ENV（如 `PLAYWRIGHT_BROWSERS_PATH`）→ 浏览器同时软链到 `/root/.cache/ms-playwright` 与 `/home/user/.cache/ms-playwright`；
- Playwright 1.60 的 Chromium 目录是 `chrome-linux64/`（历史版本为 `chrome-linux/`）→ `browser-kiosk.sh` 用 `chrome-linux*/chrome` 匹配。

## 发布镜像（CI → Docker Hub）

沙盒镜像由 `.github/workflows/ci.yml` 的 `sandbox` job 自动构建并推 Docker Hub，**不再手工推 CCR/TCR**：

- 触发：push `main`，或手动 `gh workflow run ci.yml`
- 平台：`linux/amd64`
- 仓库：`docker.io/${{ secrets.DOCKERHUB_USERNAME }}/ai-game-platform-sandbox`
- tag：`sha-<40位 commit>`（AGS 工具引用这个，保证不可变）+ `main`

GitHub 仓库需要两个 secrets：`DOCKERHUB_USERNAME`、`DOCKERHUB_TOKEN`（Docker Hub PAT）。

本地应急构建（可选；正常不需要）：

```bash
cd sandbox
docker build -f image/Dockerfile --platform=linux/amd64 \
  -t <DOCKERHUB_USERNAME>/ai-game-platform-sandbox:local .
docker push <DOCKERHUB_USERNAME>/ai-game-platform-sandbox:local
```

## 创建 / 更新 AGS 工具

工具创建时会**解析并锁定镜像 digest**，不支持原地换镜像；镜像更新后必须新建工具并更新 `apps/.env` 的 `AGS_TEMPLATE`。

AGS 拉 Docker Hub 建议走腾讯云的 Docker Hub 镜像站 `mirror.ccs.tencentyun.com`（上海/香港 AGS 都能到）；也可以直接写 `docker.io/...`，以工具状态为准：

```bash
agr tool create -n ai-game-platform-sandbox-hk -t custom --region ap-hongkong \
  -d "AI 游戏平台沙盒：浏览器(NoVNC)+Node24+Playwright+envd" \
  --network-configuration '{"NetworkMode":"PUBLIC"}' \
  --role-arn qcs::cam::uin/100037354656:roleName/ai-game-platform-test-role \
  --storage-mounts '[{"Name":"work","MountPath":"/workspace/work","StorageSource":{"Cos":{"BucketName":"ai-game-platform-hk-1327210567","BucketPath":"/games","Endpoint":"ai-game-platform-hk-1327210567.cos.ap-hongkong.myqcloud.com"}}}]' \
  --custom-configuration '{
    "Image": "mirror.ccs.tencentyun.com/<DOCKERHUB_USERNAME>/ai-game-platform-sandbox:sha-<commit>",
    "ImageRegistryType": "custom",
    "Command": ["/bin/bash"],
    "Args": ["-lc", "/opt/sandbox/entrypoint.sh"],
    "Ports": [
      {"Name": "novnc", "Port": 9000, "Protocol": "TCP"},
      {"Name": "envd", "Port": 49983, "Protocol": "TCP"}
    ],
    "Resources": {"CPU": "1000m", "Memory": "1Gi", "Storage": "10Gi"},
    "Probe": {
      "HttpGet": {"Path": "/health", "Port": 49983, "Scheme": "HTTP"},
      "ReadyTimeoutMs": 30000, "ProbeTimeoutMs": 3000, "ProbePeriodMs": 3000,
      "SuccessThreshold": 1, "FailureThreshold": 100
    }
  }' \
  --wait
```

- Docker Hub 是公开仓库（`custom` 类型），工具角色**不再需要** `QcloudAccessForAgsTcrRead`，只需 `QcloudAccessForAgsCosReadWrite`（COS 挂载）；
- 工具 `Status=FAILED` 时先看 `StatusReason`：`image not found` = 镜像还没推完/tag 写错；`AuthFailure` = 镜像不是 public 或 registry 类型不对；
- 实例级素材挂载（`x-mounts` 子路径）仍由 api `AgsGateway.ensure` 传入，custom 工具同样支持；
- 规格按需调整：`Resources.CPU/Memory`、`Storage`（1/5/10/20GiB，默认 1GiB 不够用）。
  AGS 只允许 **CPU:Memory = 1:1 / 1:2 / 2:1**（CPU 档位 0.5/1/2/4/8/16/32 核，内存 1Gi 步进）：
  0.5 核只能配 1Gi、1 核只能配 1–2Gi、2 核可配 1/2/4Gi……`0.5C4G`、`1C4G` 都会被 AGS 拒绝
  （`InvalidParameterValue.ResourceSpecification`）；
- **当前规格为 1C1G（`1000m` / `1Gi` / `10Gi`）**，2026-11-26 由 1C2G 下调（成本）；1C1G 下 Chromium + Node + esbuild 实测可用，但内存余量约 370 MiB，复杂游戏需观察 OOM；
- 规格可**原地更新**（只影响之后新建的实例，不用改代码/`.env`）：
  ```bash
  agr tool get <tool-id> -o json > before.json   # 备份
  # 取 .Data.CustomConfiguration，删掉只读的 ImageDigest，只改 Resources，再回写
  jq '.Data.CustomConfiguration | del(.ImageDigest) | .Resources = {"CPU":"1000m","Memory":"1Gi","Storage":"10Gi"}' \
    before.json > custom.json
  agr tool update <tool-id> --custom-configuration @custom.json --wait
  ```

## 本地冒烟（可选）

```bash
docker run --rm -it -p 49983:49983 -p 9000:9000 <DOCKERHUB_USERNAME>/ai-game-platform-sandbox:sha-<commit>
# 容器内起游戏服务后，浏览器窗口会自动打开；本机浏览器访问 noVNC：
#   http://localhost:9000/novnc/vnc.html?path=websockify&autoconnect=1&resize=scale
```

验收脚本：`docs/chat/10.11/scripts/verify_sandbox_tool.py`。
