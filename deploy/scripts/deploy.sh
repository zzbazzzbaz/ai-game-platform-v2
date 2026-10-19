#!/usr/bin/env bash
# 服务器侧部署入口（CI 与手工共用；幂等；回滚同样是换 TAG 再跑一次）
#   TAG=sha-<commit> scripts/deploy.sh
set -euo pipefail
cd "$(dirname "$0")/.."

TAG="${TAG:?用法: TAG=sha-xxxx scripts/deploy.sh}"
export TAG

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

# 兜底修权限：initdb 脚本需容器内 postgres(999) 可读，Caddyfile 需 caddy(999) 可读；.env 保持 600
chmod 755 scripts/*.sh initdb/*.sh 2>/dev/null || true
chmod 644 caddy/Caddyfile docker-compose.yml 2>/dev/null || true

echo "==> 拉取镜像（TAG=$TAG）"
docker compose --env-file .env pull

echo "==> 重建容器"
docker compose --env-file .env up -d --remove-orphans

echo "==> 重载 Caddy"
if ! sudo -n systemctl reload caddy 2>/dev/null; then
	echo "警告：未能自动重载 Caddy（检查 /etc/sudoers.d/ai-game-deploy）" >&2
fi

docker image prune -f
docker compose --env-file .env ps
