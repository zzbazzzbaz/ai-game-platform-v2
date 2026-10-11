# 沙盒镜像（AGS custom 工具）

单容器提供 agent 工作所需的全部能力，替代 AGS `aio` 预置类型：

| 能力 | 组件 |
|---|---|
| 浏览器 | Xvfb（:0，1280x720）+ x11vnc + noVNC/websockify（**9000**）+ Chromium 应用窗口（自动打开 `http://localhost:3000`） |
| 程序执行 | envd（**49983**，命令/文件接口）+ Node 20 + Python3 + Playwright（Python/Node，Chromium 已装） |
| 工作区 | `/workspace/work`（COS 挂载；为空时 entrypoint 从镜像模板播种）、`/workspace/input`（只读） |
| 预装资产 | 游戏模板及依赖 `/opt/game-template`（`npm ci` 已烘焙，工作区软链 `node_modules`）、技能库 `/opt/skills` |

启动顺序（`image/entrypoint.sh`）：播种工作区 → Xvfb/x11vnc/websockify → 等游戏服务就绪后拉起 Chromium（`image/browser-kiosk.sh`，崩溃自动重启）→ 前台运行 envd。

两个已踩的坑（勿回退）：

- **envd 命令只继承 PATH**，不会带镜像 ENV（如 `PLAYWRIGHT_BROWSERS_PATH`）→ 浏览器同时软链到 `/root/.cache/ms-playwright` 与 `/home/user/.cache/ms-playwright`；
- Playwright 1.60 的 Chromium 目录是 `chrome-linux64/`（历史版本为 `chrome-linux/`）→ `browser-kiosk.sh` 用 `chrome-linux*/chrome` 匹配。

## 发布镜像

必须 `linux/amd64`（Apple Silicon 亦显式指定）；构建上下文为 `sandbox/` 目录。
**每次发布使用新的 rev 标签**（`rev1`、`rev2`…）——重复使用旧标签时，CCR 边缘缓存可能让 AGS 解析到旧 digest：

```bash
cd sandbox
docker login ccr.ccs.tencentyun.com
docker build -f image/Dockerfile --platform=linux/amd64 \
  -t ccr.ccs.tencentyun.com/aigame/sandbox:rev3 .
docker push ccr.ccs.tencentyun.com/aigame/sandbox:rev3
```

## 创建 / 更新 AGS 工具

工具创建时会**解析并锁定镜像 digest**，不支持原地换镜像；镜像更新后必须新建工具并更新 `apps/.env` 的 `AGS_TEMPLATE`：

```bash
agr tool create -n ai-game-platform-sandbox -t custom \
  -d "AI 游戏平台沙盒：浏览器(NoVNC)+Node20+Playwright+envd" \
  --network-configuration '{"NetworkMode":"PUBLIC"}' \
  --role-arn qcs::cam::uin/100037354656:roleName/ai-game-platform-test-role \
  --storage-mounts '[{"Name":"work","MountPath":"/workspace/work","StorageSource":{"Cos":{"BucketName":"ai-game-platform-test-1327210567","BucketPath":"/games","Endpoint":"ai-game-platform-test-1327210567.cos.ap-shanghai.myqcloud.com"}}}]' \
  --custom-configuration '{
    "Image": "ccr.ccs.tencentyun.com/aigame/sandbox:rev3",
    "ImageRegistryType": "personal",
    "Command": ["/bin/bash"],
    "Args": ["-lc", "/opt/sandbox/entrypoint.sh"],
    "Ports": [
      {"Name": "novnc", "Port": 9000, "Protocol": "TCP"},
      {"Name": "envd", "Port": 49983, "Protocol": "TCP"}
    ],
    "Resources": {"CPU": "2000m", "Memory": "4Gi", "Storage": "10Gi"},
    "Probe": {
      "HttpGet": {"Path": "/health", "Port": 49983, "Scheme": "HTTP"},
      "ReadyTimeoutMs": 30000, "ProbeTimeoutMs": 3000, "ProbePeriodMs": 3000,
      "SuccessThreshold": 1, "FailureThreshold": 100
    }
  }' \
  --wait
```

- 工具角色需具备 **`QcloudAccessForAgsTcrRead`**（拉取 CCR 镜像）+ `QcloudAccessForAgsCosReadWrite`（COS 挂载）——缺前者时工具会 `AuthFailure.Registry: tcr:DescribeImagePersonal` 失败；
- 实例级素材挂载（`x-mounts` 子路径）仍由 api `AgsGateway.ensure` 传入，custom 工具同样支持；
- 规格按需调整：`Resources.CPU/Memory`（如 `4000m`/`8Gi`）、`Storage`（1/5/10/20GiB，默认 1GiB 不够用）。

## 本地冒烟（可选）

```bash
docker run --rm -it -p 49983:49983 -p 9000:9000 ccr.ccs.tencentyun.com/aigame/sandbox:rev3
# 容器内起游戏服务后，浏览器窗口会自动打开；本机浏览器访问 noVNC：
#   http://localhost:9000/novnc/vnc.html?path=websockify&autoconnect=1&resize=scale
```

验收脚本：`docs/chat/10.11/scripts/verify_sandbox_tool.py`。
