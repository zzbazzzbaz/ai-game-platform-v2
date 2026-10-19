#!/usr/bin/env bash
# AI 游戏平台 · 服务器侧部署入口（CI 与手工共用；幂等；回滚也走它）
#
# 用法：
#   首次 / 升级：TAG=sha-<commit> scripts/deploy.sh
#   回滚        ：TAG=sha-<上一个 commit> scripts/deploy.sh
#
# 前置：/srv/ai-game-platform/.env（唯一业务配置源，chmod 600，不进 git）
set -euo pipefail
cd "$(dirname "$0")/.."

TAG="${TAG:?用法: TAG=sha-xxxx scripts/deploy.sh}"
export TAG

# Caddy 配置里的 {$DOMAIN} / {$ACME_EMAIL} 来自 caddy.env（与 systemd 同源）
if [ -f caddy.env ]; then
	set -a
	# shellcheck disable=SC1091
	. ./caddy.env
	set +a
fi

echo "==> 校验 Caddyfile"
if [ -f caddy/Caddyfile ]; then
	caddy validate --config caddy/Caddyfile
fi

# 兜底修复权限位：容器内的 postgres 需要可读可执行（CI/scp 传输可能丢位）
chmod 755 scripts/*.sh initdb/*.sh 2>/dev/null || true

echo "==> 拉取镜像（TAG=$TAG）"
docker compose --env-file .env pull

echo "==> 重建容器"
docker compose --env-file .env up -d --remove-orphans

echo "==> 重载 Caddy（配置或容器重建后生效）"
if ! sudo -n systemctl reload caddy 2>/dev/null; then
	echo "警告：未能自动重载 Caddy（检查 /etc/sudoers.d/ai-game-deploy），请手工执行 sudo systemctl reload caddy" >&2
fi

echo "==> 清理旧镜像"
docker image prune -f

echo "==> 当前状态"
docker compose --env-file .env ps
