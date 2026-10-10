#!/usr/bin/env python3
"""把游戏模板 / skills / init.sh 发布到 COS `platform/` 前缀（api 运行时从此读取）。

用法（仓库根）：
    make sandbox-assets-publish
 或：
    cd sandbox && uv run --env-file ../apps/.env --with cos-python-sdk-v5 python publish_assets.py

产物：
    platform/game-template/**   游戏工程模板（建游戏时复制到 games/{game_id}/）
    platform/sandbox/skills.tar.gz  技能库压缩包（初始化时解到 /opt/skills）
    platform/sandbox/init.sh        沙盒初始化脚本
"""

import io
import os
import sys
import tarfile
from pathlib import Path

from qcloud_cos import CosConfig, CosS3Client

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
TEMPLATE_DIR = REPO / "sandbox" / "game-template"
SKILLS_DIR = HERE / "assets" / "skills"

IGNORED_PARTS = {"node_modules", "dist", ".runtime", ".git", ".DS_Store"}
REQUIRED_ENV = ("COS_SECRET_ID", "COS_SECRET_KEY", "COS_REGION", "COS_BUCKET")


def main() -> None:
    missing = [key for key in REQUIRED_ENV if not os.environ.get(key)]
    if missing:
        sys.exit(f"缺少环境变量：{', '.join(missing)}")
    if not TEMPLATE_DIR.is_dir() or not SKILLS_DIR.is_dir():
        sys.exit("模板或 skills 目录不存在，请检查仓库结构")

    prefix = os.environ.get("COS_PLATFORM_PREFIX", "platform").strip("/")
    bucket = os.environ["COS_BUCKET"]
    client = CosS3Client(
        CosConfig(
            Region=os.environ["COS_REGION"],
            SecretId=os.environ["COS_SECRET_ID"],
            SecretKey=os.environ["COS_SECRET_KEY"],
            Scheme="https",
        )
    )

    count = 0
    for path in sorted(TEMPLATE_DIR.rglob("*")):
        rel = path.relative_to(TEMPLATE_DIR)
        if path.is_dir() or any(part in IGNORED_PARTS for part in rel.parts):
            continue
        client.put_object(
            Bucket=bucket,
            Key=f"{prefix}/game-template/{rel.as_posix()}",
            Body=path.read_bytes(),
        )
        count += 1

    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        tar.add(SKILLS_DIR, arcname=".")
    client.put_object(
        Bucket=bucket, Key=f"{prefix}/sandbox/skills.tar.gz", Body=buf.getvalue()
    )

    client.put_object(
        Bucket=bucket, Key=f"{prefix}/sandbox/init.sh", Body=(HERE / "init.sh").read_bytes()
    )

    print(f"已发布到 cos://{bucket}/{prefix}/：模板 {count} 个文件、skills.tar.gz、init.sh")


if __name__ == "__main__":
    main()
