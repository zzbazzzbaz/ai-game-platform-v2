#!/usr/bin/env bash
# 服务器一次性初始化（sudo 执行，幂等）
#   sudo DOMAIN=ai-game-platform.test.chatgqt.top ACME_EMAIL=you@example.com bash deploy/scripts/bootstrap.sh
set -euo pipefail

DOMAIN="${DOMAIN:-ai-game-platform.test.chatgqt.top}"
ACME_EMAIL="${ACME_EMAIL:-admin@chatgqt.top}"
DEPLOY_USER="${DEPLOY_USER:-guoqitong}"
ROOT="${DEPLOY_ROOT:-/srv/ai-game-platform}"
API_UID=10001   # api 镜像里的 app 用户（deploy/docker/api.Dockerfile）
PG_UID=999      # postgres 官方镜像里的 postgres 用户

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }

if [ "$(id -u)" -ne 0 ]; then
	echo "请用 sudo 执行本脚本" >&2
	exit 1
fi

log "1/6 docker 免 sudo：$DEPLOY_USER 加入 docker 组"
usermod -aG docker "$DEPLOY_USER"
getent group docker

log "2/6 安装系统级 Caddy"
if ! command -v caddy >/dev/null 2>&1; then
	apt-get update -qq
	DEBIAN_FRONTEND=noninteractive apt-get install -y -qq caddy
fi
caddy version

log "3/6 部署目录与日志目录"
install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 755 "$ROOT"
install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 755 "$ROOT"/{caddy,initdb,scripts,secrets,backups}
# secrets 子目录必须 755：容器内以 uid 999/10001 读挂载目录，700 会无法遍历
install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 755 "$ROOT/secrets/jwt"
install -d -o "$DEPLOY_USER" -g "$DEPLOY_USER" -m 755 "$ROOT/secrets/pg-tls"
install -d -o caddy -g caddy -m 755 /var/log/caddy

log "4/6 Caddy 变量与受限 reload 规则"
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

cat >/etc/sudoers.d/ai-game-deploy <<EOF
$DEPLOY_USER ALL=(root) NOPASSWD: /usr/bin/systemctl reload caddy
EOF
chmod 440 /etc/sudoers.d/ai-game-deploy
visudo -c -f /etc/sudoers.d/ai-game-deploy >/dev/null

log "5/6 游戏库 TLS 自签证书"
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

log "6/6 api 的 JWT 密钥对"
if [ ! -f "$ROOT/secrets/jwt/jwt_private.pem" ]; then
	openssl genpkey -algorithm RSA -pkeyopt rsa_keygen_bits:2048 \
		-out "$ROOT/secrets/jwt/jwt_private.pem" 2>/dev/null
	openssl rsa -pubout -in "$ROOT/secrets/jwt/jwt_private.pem" \
		-out "$ROOT/secrets/jwt/jwt_public.pem" 2>/dev/null
fi
chown "$API_UID:$API_UID" "$ROOT/secrets/jwt/jwt_private.pem" "$ROOT/secrets/jwt/jwt_public.pem"
chmod 600 "$ROOT/secrets/jwt/jwt_private.pem"
chmod 644 "$ROOT/secrets/jwt/jwt_public.pem"

# Caddy 启动前 /etc/caddy/Caddyfile 必须存在：首次部署前放占位配置
if [ ! -s "$ROOT/caddy/Caddyfile" ]; then
	printf '{\n\temail %s\n}\n\n%s {\n\trespond "waiting for deploy" 503\n}\n' \
		"$ACME_EMAIL" "$DOMAIN" >"$ROOT/caddy/Caddyfile"
fi
chown "$DEPLOY_USER:$DEPLOY_USER" "$ROOT/caddy/Caddyfile"
chmod 644 "$ROOT/caddy/Caddyfile"
ln -sfn "$ROOT/caddy/Caddyfile" /etc/caddy/Caddyfile

systemctl daemon-reload
systemctl enable --now caddy
systemctl reload caddy || systemctl restart caddy

log "附加：每日备份 timer"
cat >/etc/systemd/system/ai-game-backup.service <<EOF
[Unit]
Description=AI 游戏平台 · 每日数据库备份（pg_dump + 上传 COS）
After=docker.service
Requires=docker.service

[Service]
Type=oneshot
User=$DEPLOY_USER
WorkingDirectory=$ROOT
ExecStart=$ROOT/scripts/backup.sh
StandardOutput=append:$ROOT/backups/backup.log
StandardError=append:$ROOT/backups/backup.log
EOF
cat >/etc/systemd/system/ai-game-backup.timer <<'EOF'
[Unit]
Description=AI 游戏平台 · 每日 04:00 触发备份

[Timer]
OnCalendar=*-*-* 04:00:00
Persistent=true
RandomizedDelaySec=300

[Install]
WantedBy=timers.target
EOF
systemctl daemon-reload
systemctl enable --now ai-game-backup.timer

log "完成：$ROOT（下一步把 .env 放到该目录并执行 scripts/deploy.sh）"
