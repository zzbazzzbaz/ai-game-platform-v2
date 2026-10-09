#!/usr/bin/env bash
# AGS 沙盒初始化（aio 预置类型）：skills / 依赖 / 软链。
# 由 api 经 COS 下发执行（root）；幂等：api 看到 /opt/.aigame-init-done 会跳过本脚本。
#
# 契约（与 apps/api/app/core/constants.py、apps/agent/agent/core/constants.py 同步）：
#   /workspace/work   游戏工程（COS 挂载，唯一可写区）
#   /workspace/input  用户素材（COS 挂载，只读）
#   /opt/deps         node_modules（不进挂载层：COS 大量小文件性能差）
#   /opt/skills       Phaser 技能库（deepagents 经沙盒 backend 读取 SKILL.md）
set -euo pipefail

WORK_ROOT="/workspace/work"
DEPS_ROOT="/opt/deps"
SKILLS_ROOT="/opt/skills"
SKILLS_TMP="/tmp/skills.tar.gz"
INIT_MARKER="/opt/.aigame-init-done"

# 1) skills（api 会先写入 /tmp/skills.tar.gz）
if [ -f "$SKILLS_TMP" ]; then
  mkdir -p "$SKILLS_ROOT"
  tar -xzf "$SKILLS_TMP" -C "$SKILLS_ROOT"
  rm -f "$SKILLS_TMP"
fi

# 2) 依赖：按工作区的 package.json/package-lock.json 安装到 /opt/deps（重建沙盒时重装）
if [ ! -d "$DEPS_ROOT/node_modules" ]; then
  mkdir -p "$DEPS_ROOT"
  cp "$WORK_ROOT/package.json" "$WORK_ROOT/package-lock.json" "$DEPS_ROOT/"
  cd "$DEPS_ROOT"
  npm config set registry https://mirrors.cloud.tencent.com/npm/ || true
  npm ci --no-audit --no-fund
fi

# 3) 软链：工作区可见 node_modules，但实体不落 COS
if [ ! -e "$WORK_ROOT/node_modules" ]; then
  ln -s "$DEPS_ROOT/node_modules" "$WORK_ROOT/node_modules"
fi

touch "$INIT_MARKER"
echo "[init] done"
