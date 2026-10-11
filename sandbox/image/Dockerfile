# AI 游戏平台 · AGS 沙盒镜像（custom 工具用）
#
# 单容器提供两类能力：
#   浏览器：Xvfb + x11vnc + noVNC/websockify(:9000) + Chromium（预览窗口直开 localhost:3000）
#   执行：envd(:49983 命令/文件) + Node 20 + Python3/Playwright（agent 截图自检）
# 资产烘焙：游戏模板及依赖（/opt/game-template）、Phaser 技能库（/opt/skills）
#
# 构建（必须 linux/amd64；上下文为 sandbox/ 目录）：
#   cd sandbox && docker build -f image/Dockerfile --platform=linux/amd64 \
#     -t ccr.ccs.tencentyun.com/aigame/sandbox:v1 .
FROM node:20-bookworm-slim

# AGS 管理守护进程（官方镜像仅提供 /usr/bin/envd 二进制）
COPY --from=ccr.ccs.tencentyun.com/ags-image/envd:v0.5.14 --chmod=755 /usr/bin/envd /usr/bin/envd

ENV DEBIAN_FRONTEND=noninteractive \
    LANG=C.UTF-8 \
    PLAYWRIGHT_BROWSERS_PATH=/opt/ms-playwright \
    PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# 系统依赖：基础工具 + 浏览器栈 + 中文字体 + Python（Chromium 运行库由 playwright install-deps 补齐）
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl git less procps psmisc tar unzip xz-utils \
      python3 python3-pip python3-venv \
      xvfb x11vnc novnc websockify \
      fonts-noto-cjk fonts-noto-color-emoji

# Playwright（Node CLI + Python 包；版本一致以保证共用同一份浏览器文件）
ARG PLAYWRIGHT_VERSION=1.60.0
RUN npm install -g playwright@${PLAYWRIGHT_VERSION} \
 && pip3 install --no-cache-dir --break-system-packages playwright==${PLAYWRIGHT_VERSION} \
 && playwright install --with-deps chromium \
 && rm -rf /var/lib/apt/lists/*

# 游戏模板 + 依赖（烘焙进镜像；运行时由 entrypoint 播种工作区并软链 node_modules）
COPY game-template/ /opt/game-template/
RUN cd /opt/game-template \
 && npm config set registry https://mirrors.cloud.tencent.com/npm/ \
 && npm ci --no-audit --no-fund \
 && npm cache clean --force

# Phaser 技能库（agent 以 skills=[/opt/skills] 读取）
COPY assets/skills/ /opt/skills/

# noVNC 站点：/novnc/vnc.html + websockify 路径（与 api 预览地址契约一致）
RUN mkdir -p /opt/novnc-web && cp -r /usr/share/novnc /opt/novnc-web/novnc

# 启动脚本 + 普通用户（envd 文件接口默认按 user 解析）；
# envd 命令只继承 PATH、不带 PLAYWRIGHT_BROWSERS_PATH → 浏览器软链到默认查找路径
COPY image/entrypoint.sh image/browser-kiosk.sh image/prepare-workspace.sh /opt/sandbox/
RUN chmod +x /opt/sandbox/entrypoint.sh /opt/sandbox/browser-kiosk.sh /opt/sandbox/prepare-workspace.sh \
 && useradd -m -s /bin/bash user \
 && mkdir -p /workspace/work /workspace/input \
 && mkdir -p /root/.cache /home/user/.cache \
 && ln -s /opt/ms-playwright /root/.cache/ms-playwright \
 && ln -s /opt/ms-playwright /home/user/.cache/ms-playwright \
 && chown -R user:user /home/user

EXPOSE 49983 9000

# AGS 工具启动命令：/bin/bash -lc /opt/sandbox/entrypoint.sh（本地 docker run 亦同）
CMD ["/bin/bash", "-lc", "/opt/sandbox/entrypoint.sh"]
