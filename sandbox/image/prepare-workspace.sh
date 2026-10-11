#!/bin/bash
# 工作区准备（可独立执行、幂等）：
#   1. COS 挂载为空时，从镜像模板 /opt/game-template 播种到 /workspace/work
#   2. node_modules 软链到镜像内依赖（不进 COS 挂载层）
# 旧 aio 沙盒留下指向 /opt/deps/node_modules 的软链在本镜像中是悬空的 → 重新指向。
set -u

TEMPLATE=/opt/game-template
WORK=/workspace/work
NM="$WORK/node_modules"

if [ ! -f "$WORK/package.json" ] && [ -d "$TEMPLATE" ]; then
  echo "[prepare] 播种工作区：$TEMPLATE → $WORK"
  mkdir -p "$WORK"
  (cd "$TEMPLATE" && tar --exclude=./node_modules --exclude=./.runtime --exclude=./dist -cf - .) \
    | (cd "$WORK" && tar -xf -)
fi

if [ -d "$TEMPLATE/node_modules" ] && [ ! -e "$NM" ]; then
  [ -L "$NM" ] && rm -f "$NM"
  ln -s "$TEMPLATE/node_modules" "$NM" \
    && echo "[prepare] node_modules → $TEMPLATE/node_modules"
fi
