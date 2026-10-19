#!/bin/bash
# 游戏库首启初始化：把官方的明文规则 `host all all all` 换成 `hostssl`，远程只允许 TLS
set -euo pipefail

HBA="${PGDATA}/pg_hba.conf"

if [ ! -f "$HBA" ]; then
	echo "[initdb] 找不到 $HBA，跳过" >&2
	exit 0
fi

sed -i -E '/^host[[:space:]]+all[[:space:]]+all[[:space:]]+all[[:space:]]/d' "$HBA"

if ! grep -qE '^hostssl[[:space:]]+all[[:space:]]+all[[:space:]]+all[[:space:]]+scram-sha-256' "$HBA"; then
	echo 'hostssl all all all scram-sha-256' >>"$HBA"
fi

echo "[initdb] pg_hba.conf 已强制 hostssl（远程连接必须 TLS）"
