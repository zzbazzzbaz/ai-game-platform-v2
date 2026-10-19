#!/usr/bin/env bash
# 每日备份：本机保留 7 天 + 上传 COS（systemd timer ai-game-backup.timer 调用）
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

echo "==> 平台元数据库"
docker compose exec -T postgres-platform \
	pg_dump -Fc -U "$POSTGRES_PLATFORM_USER" -d "$POSTGRES_PLATFORM_DB" >"$PLATFORM_DUMP"

echo "==> 游戏库整实例"
docker compose exec -T postgres-games pg_dumpall -U postgres | gzip -9 >"$GAMES_DUMP"

find "$DEST" -type f \( -name 'games-*.sql.gz' -o -name 'platform-*.dump' \) -mtime +7 -delete

if [ -n "${COS_BUCKET:-}" ] && [ -n "${COS_SECRET_ID:-}" ]; then
	echo "==> 上传 COS: $COS_BUCKET"
	for f in "$PLATFORM_DUMP" "$GAMES_DUMP"; do
		# -i 必需：python 从 stdin 读脚本，缺了会静默不执行
		docker run --rm -i --env-file ./.env -v "$PWD/backups:/backups:ro" \
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

ls -lh "$DEST" | tail -n 5
