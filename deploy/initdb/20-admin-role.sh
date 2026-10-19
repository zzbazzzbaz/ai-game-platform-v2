#!/bin/bash
# 游戏库初始化：创建平台管理员角色（非 superuser；pg 官方入口在首启时执行本目录脚本）
#
# 必需环境变量（由 compose 注入）：GAMES_ADMIN_USER / GAMES_ADMIN_PASSWORD
# 说明：pg_ctl 首次初始化才会执行本脚本，容器重启不会重复执行（幂等仍然保留）。
set -euo pipefail

: "${GAMES_ADMIN_USER:?缺少 GAMES_ADMIN_USER}"
: "${GAMES_ADMIN_PASSWORD:?缺少 GAMES_ADMIN_PASSWORD}"

echo "[initdb] 创建游戏库管理员角色 ${GAMES_ADMIN_USER}（CREATEDB CREATEROLE，非 superuser）"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname postgres \
	-v admin_user="$GAMES_ADMIN_USER" \
	-v admin_pw="$GAMES_ADMIN_PASSWORD" <<-'SQL'
	SELECT format('CREATE ROLE %I LOGIN CREATEDB CREATEROLE PASSWORD %L', :'admin_user', :'admin_pw')
	WHERE NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = :'admin_user')
	\gexec
SQL

echo "[initdb] 管理员角色就绪"
