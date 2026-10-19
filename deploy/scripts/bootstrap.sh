#!/usr/bin/env bash
# AI 游戏平台 · 服务器一次性初始化（需要 sudo 执行，幂等可重复运行）
#
# 做四件事：
#   1. 让部署用户免 sudo 使用 docker（CI 部署前提）
#   2. 安装并启用系统级 Caddy（公网 80/443 唯一入口）
#   3. 建部署目录 /srv/ai-game-platform（必须可被 caddy 用户遍历，故不放 /home）
#   4. 生成游戏库 TLS 自签证书与 api 的 JWT 密钥对
#
# 用法：
#   sudo DOMAIN=ai-game-platform.test.chatgqt.top ACME_EMAIL=you@example.com \
#        bash deploy/scripts/bootstrap.sh
set -euo pipefail

DOMAIN="${DOMAIN:-ai-game-platform.test.chatgqt.top}"
ACME_EMAIL="${ACME_EMAIL:-admin@chatgqt.top}"
DEPLOY_USER="${DEPLOY_USER:-guoqitong}"
ROOT="${DEPLOY_ROOT:-/srv/ai-game-platform}"

# 容器内固定 uid：api 镜像里的 app 用户（见 deploy/docker/api.Dockerfile）
API_UID=10001
# postgres 官方镜像里的 postgres 用户
PG_UID=999

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

if [ "$(id -u)" -ne 0 ]; then
	echo "请用 sudo 执行本脚本" >&2
	exit 1
fi

log "1/6 docker 免 sudo：$DEPLOY_USER 加入 docker 组"
usermod -aG docker "$DEPLOY_USER"
getent group docker

log "2/6 安装系统级 Caddy（Ubuntu 仓库）"
if ! command -v caddy >/dev/null 2>&1; then
	apt-get update -qq
	DEBIAN_FRONTEND=noninteractive apt-get install -y -qq caddy
fi
caddy version

log "3/6 部署目录与日志目录"
install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 755 "$ROOT"
install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 755 "$ROOT"/{caddy,initdb,scripts,secrets,backups}
# 注意：这两个目录必须 755 —— 容器内以 uid 999(游戏库)/10001(api) 读取挂载目录，
# 700 会让容器内的进程无法遍历目录（文件本身仍然是 600/644）。
install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 755 "$ROOT/secrets/jwt"
install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 755 "$ROOT/secrets/pg-tls"
install -d -o caddy -g caddy -m 755 /var/log/caddy

log "4/6 Caddy 环境变量（域名 / ACME 邮箱）"
cat >"$ROOT/caddy.env" <<EOF
DOMAIN=$DOMAIN
ACME_EMAIL=$ACME_EMAIL
EOF
chown "$DEPLOY_USER:$DEPLOY_USER" "$ROOT/caddy.env"
chmod 644 "$ROOT/caddy.env"

install -d -m 755 /etc/systemd/system/caddy.service.d
cat >/etc/systemd/system/caddy.service.d/override.conf <<EOF
[Service]
EnvironmentFile=$ROOT/caddy.env
EOF

# 受限的 reload 规则：CI 只能重载 Caddy，不能执行其它 root 命令
cat >/etc/sudoers.d/ai-game-deploy <<EOF
$DEPLOY_USER ALL=(root) NOPASSWD: /usr/bin/systemctl reload caddy
EOF
chmod 440 /etc/sudoers.d/ai-game-deploy
visudo -c -f /etc/sudoers.d/ai-game-deploy >/dev/null

log "5/6 游戏库 TLS 自签证书（postgres 容器以 uid $PG_UID 读取）"
if [ ! -f "$ROOT/secrets/pg-tls/server.crt" ]; then
	openssl req -x509 -nodes -newkey rsa:2048 -days 3650 \
		-keyout "$ROOT/secrets/pg-tls/server.key" \
		-out "$ROOT/secrets/pg-tls/server.crt" \
		-subj "/CN=ai-game-platform-games-db" \
		-addext "subjectAltName=DNS:postgres-games,IP:${DEPLOY_HOST:-43.129.212.75}" 2>/dev/null
fi
chown "$PG_UID:$PG_UID" "$ROOT/secrets/pg-tls/server.key" "$ROOT/secrets/pg-tls/server.crt"
chmod 600 "$ROOT/secrets/pg-tls/server.key"
chmod 644 "$ROOT/secrets/pg-tls/server.crt"
ls -l "$ROOT/secrets/pg-tls"

log "6/6 api 的 JWT 密钥对（容器内以 uid $API_UID 读取）"
if [ ! -f "$ROOT/secrets/jwt/jwt_private.pem" ]; then
	openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
		-out "$ROOT/secrets/jwt/jwt_private.pem" 2>/dev/null
	openssl rsa -pubout -in "$ROOT/secrets/jwt/jwt_private.pem" \
		-out "$ROOT/secrets/jwt/jwt_public.pem" 2>/dev/null
fi
chown "$API_UID:$API_UID" "$ROOT/secrets/jwt/jwt_private.pem" "$ROOT/secrets/jwt/jwt_public.pem"
chmod 600 "$ROOT/secrets/jwt/jwt_private.pem"
chmod 644 "$ROOT/secrets/jwt/jwt_public.pem"
ls -l "$ROOT/secrets/jwt"

# Caddy 启动前必须存在 /etc/caddy/Caddyfile（首次部署前放一个占位配置）
if [ ! -s "$ROOT/caddy/Caddyfile" ]; then
	printf '{\n\temail %s\n}\n\n%s {\n\trespond "waiting for deploy" 503\n}\n' \
		"$ACME_EMAIL" "$DOMAIN" >"$ROOT/caddy/Caddyfile"
	chown "$DEPLOY_USER:$DEPLOY_USER" "$ROOT/caddy/Caddyfile"
fi
chmod 644 "$ROOT/caddy/Caddyfile"
ln -sfn "$ROOT/caddy/Caddyfile" /etc/caddy/Caddyfile

systemctl daemon-reload
systemctl enable --now caddy
systemctl reload caddy || systemctl restart caddy

log "完成"
cat <<EOF

部署目录      : $ROOT
Caddy 配置    : /etc/caddy/Caddyfile → $ROOT/caddy/Caddyfile
Caddy 变量    : $ROOT/caddy.env（DOMAIN=$DOMAIN，ACME_EMAIL=$ACME_EMAIL）
日志          : /var/log/caddy/access.log（journalctl -u caddy 看进程日志）

后续（CI 或手工）：
  1. 把 deploy/.env 放到 $ROOT/.env（chmod 600）—— 由 ops 维护，不进 git
  2. TAG=sha-xxxx $ROOT/scripts/deploy.sh
  3. 定时备份：crontab -e 增加
     0 4 * * * $ROOT/scripts/backup.sh >> $ROOT/backups/backup.log 2>&1
EOF
