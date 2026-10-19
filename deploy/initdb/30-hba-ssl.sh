#!/bin/bash
# 游戏库初始化：强制远程连接走 TLS
#
# 官方入口会追加 `host all all all scram-sha-256`（明文可用），这里把它替换为
# `hostssl`，只允许 TLS 连接；本地 unix socket 的 trust 规则保持不变。
set -euo pipefail

HBA="${PGDATA}/pg_hba.conf"

if [ ! -f "$HBA" ]; then
	echo "[initdb] 找不到 $HBA，跳过" >&2
	exit 0
fi

# 删除所有远程明文规则（host all all all ...）
sed -i -E '/^host[[:space:]]+all[[:space:]]+all[[:space:]]+all[[:space:]]/d' "$HBA"

if ! grep -qE '^hostssl[[:space:]]+all[[:space:]]+all[[:space:]]+all[[:space:]]+scram-sha-256' "$HBA"; then
	echo 'hostssl all all all scram-sha-256' >>"$HBA"
fi

echo "[initdb] pg_hba.conf 已强制 hostssl（远程连接必须 TLS）"
