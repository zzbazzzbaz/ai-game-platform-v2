#!/usr/bin/env bash
# AI 游戏平台 · 每日备份（本机保留 7 天 + 上传 COS）
#
# 用法：scripts/backup.sh
# 定时：crontab -e 增加
#         0 4 * * * /srv/ai-game-platform/scripts/backup.sh >> /srv/ai-game-platform/backups/backup.log 2>&1
set -euo pipefail
cd "$(dirname "$0")/.."

set -a
# shellcheck disable=SC1091
. ./.env
set +a

STAMP="$(date +%Y%m%d-%H%M%S)"
DEST="./backups"
mkdir -p "$DEST"

PLATFORM_DUMP="$DEST/platform-$STAMP.dump"
GAMES_DUMP="$DEST/games-$STAMP.sql.gz"

echo "==> 平台元数据库（-Fc）"
docker compose exec -T postgres-platform \
	pg_dump -Fc -U "$POSTGRES_PLATFORM_USER" -d "$POSTGRES_PLATFORM_DB" >"$PLATFORM_DUMP"

echo "==> 游戏库整实例（含 game_xxx 库与角色，SQL+gzip）"
docker compose exec -T postgres-games pg_dumpall -U postgres | gzip -9 >"$GAMES_DUMP"

echo "==> 保留最近 7 天"
find "$DEST" -type f \( -name 'games-*.sql.gz' -o -name 'platform-*.dump' \) -mtime +7 -delete

if [ -n "${COS_BUCKET:-}" ] && [ -n "${COS_SECRET_ID:-}" ]; then
	echo "==> 上传 COS: bucket=$COS_BUCKET"
	for f in "$PLATFORM_DUMP" "$GAMES_DUMP"; do
		# 借用 api 镜像里的 cos-python-sdk-v5；备份目录只读挂进容器
		docker run --rm --env-file ./.env -v "$PWD/backups:/backups:ro" \
			--entrypoint python "${API_IMAGE}:${TAG:-main}" - "$(basename "$f")" <<'PY'
import os
import sys

from qcloud_cos import CosConfig, CosS3Client

name = sys.argv[1]
config = CosConfig(
    Region=os.environ["COS_REGION"],
    SecretId=os.environ["COS_SECRET_ID"],
    SecretKey=os.environ["COS_SECRET_KEY"],
)
CosS3Client(config).upload_file(
    Bucket=os.environ["COS_BUCKET"],
    Key=f"backup/pg/{name}",
    LocalFilePath=f"/backups/{name}",
    EnableMD5=False,
)
print(f"[backup] 已上传 backup/pg/{name}")
PY
	done
else
	echo "跳过 COS 上传（未配置 COS_BUCKET / COS_SECRET_ID）"
fi

echo "==> 备份文件"
ls -lh "$DEST" | tail -n 5
