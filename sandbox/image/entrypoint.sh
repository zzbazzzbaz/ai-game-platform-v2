#!/bin/bash
# AGS 沙盒入口（自定义镜像）
# 顺序：播种工作区（COS 挂载为空时）→ 起浏览器栈（Xvfb/x11vnc/websockify/Chromium）→ 前台运行 envd
# 由 AGS 工具启动命令调用：/bin/bash -lc /opt/sandbox/entrypoint.sh
set -u

LOG_DIR=/tmp
SCREEN=1280x720x24
export PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
export DISPLAY=:0
export PLAYWRIGHT_BROWSERS_PATH="${PLAYWRIGHT_BROWSERS_PATH:-/opt/ms-playwright}"

log() { echo "[sandbox] $*"; }

# 崩溃自动重启（后台跑，日志落 $LOG_DIR/<name>.log）
supervise() {
  local name=$1; shift
  (
    while true; do
      "$@" >>"$LOG_DIR/$name.log" 2>&1
      log "$name 退出（code=$?），1s 后重启"
      sleep 1
    done
  ) &
}

# 1) 工作区准备：COS 挂载为空时从镜像模板播种；node_modules 软链到镜像内依赖
/opt/sandbox/prepare-workspace.sh

# 2) 虚拟显示（:0）+ VNC（5900，仅本机）+ noVNC/websockify（9000）
log "启动显示栈"
supervise xvfb bash -c "rm -f /tmp/.X0-lock; exec Xvfb :0 -screen 0 $SCREEN -nolisten tcp -ac"
for _ in $(seq 1 100); do [ -S /tmp/.X11-unix/X0 ] && break; sleep 0.1; done
supervise x11vnc x11vnc -display :0 -forever -shared -nopw -localhost -rfbport 5900 -quiet
supervise websockify websockify --web=/opt/novnc-web 9000 127.0.0.1:5900

# 3) 预览浏览器：等游戏服务就绪后打开（应用窗口=游戏画面），崩溃自动重启
/opt/sandbox/browser-kiosk.sh >>"$LOG_DIR/browser.log" 2>&1 &

# 4) envd：前台常驻（AGS 健康检查 + 命令/文件接口）
log "启动 envd"
exec /usr/bin/envd
