from __future__ import annotations

import argparse
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
SKILLS_DIR = ASSETS / "skills"
TEMPLATE_DIR = ASSETS / "templates" / "single"

IMAGE_NAME = "game-runner"
BUILDER_APP_NAME = "game-runner-builder"
BASE_IMAGE = "node:22-bookworm-slim"

SKILLS_MOUNT = "/skills"
DEPS_ROOT = "/opt/deps"
WORK_ROOT = "/workspace/work"
INPUT_ROOT = "/workspace/input"

# ---------------------------------------------------------------------------
# 沙箱内目录架构（契约）
#
#   /skills/                  Phaser 技能库；deepagents 读 /skills/*/SKILL.md
#   /opt/deps/                npm ci 安装的可复现依赖（输入 package.json + package-lock.json）
#   /workspace/input/         用户素材，只读
#   /workspace/work/          游戏工程，唯一可写区
#   └── node_modules -> /opt/deps/node_modules
#                             软链；不可做成真实目录（否则快照会把整份依赖上传 MinIO），
#                             且目标必须在 WORK_ROOT 之外（ModalGateway._walk 才会跳过）
#
# api_server / agent_server 常量按上述路径写死，改名即破坏跨服务契约；
# 改本文件或 assets/** 后需重建镜像，已存在的沙箱不会热更新。
#
# TODO(多人模式): 本镜像只有 single 一套骨架，不分单/多人。因为沙箱按 thread 创建，
# 而线程不带模式（EnsureBody 只有 thread_id、thread_owners 无模式列），建沙箱时无从区分。
# 分模式的前置：会话带模式 + 先定多人产物形态；再选「一份镜像装两套骨架」（deps 也按模式分两份）
# 或「每模式一份镜像」（api_server 需加 mode→镜像名映射）。在此之前不预埋分支。
# ---------------------------------------------------------------------------

# 这些是本地/运行时产物，不进镜像
_IGNORED_NAMES = frozenset({"node_modules", "dist", ".runtime"})


def _ignore(path: Path) -> bool:
    return path.name in _IGNORED_NAMES


def build_image() -> modal.Image:
    return (
        modal.Image.from_registry(BASE_IMAGE)
        # 依赖层：只依赖 package.json / package-lock.json，改其它骨架文件不会触发重建
        .add_local_file(TEMPLATE_DIR / "package.json", f"{DEPS_ROOT}/package.json", copy=True)
        .add_local_file(
            TEMPLATE_DIR / "package-lock.json", f"{DEPS_ROOT}/package-lock.json", copy=True
        )
        .run_commands(f"cd {DEPS_ROOT} && npm ci --no-audit --no-fund")
        .run_commands(f"cd {DEPS_ROOT} && npx playwright install --with-deps chromium")
        # 资产层：技能库 + 工程骨架（最后，便于小改快速重建）
        .add_local_dir(SKILLS_DIR, SKILLS_MOUNT, copy=True)
        .add_local_dir(TEMPLATE_DIR, WORK_ROOT, copy=True, ignore=_ignore)
        .run_commands(
            f"mkdir -p {INPUT_ROOT}",
            f"ln -s {DEPS_ROOT}/node_modules {WORK_ROOT}/node_modules",
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Build and publish the game-runner sandbox image")
    parser.add_argument(
        "--tag",
        action="append",
        required=True,
        help="镜像 tag，可重复传入（如 --tag latest --tag <sha>）",
    )
    args = parser.parse_args()

    app = modal.App.lookup(BUILDER_APP_NAME, create_if_missing=True)
    image = build_image()
    with modal.enable_output():
        image.build(app)
    for tag in args.tag:
        image.publish(f"{IMAGE_NAME}:{tag}")
        print(f"published {IMAGE_NAME}:{tag}")


if __name__ == "__main__":
    main()
