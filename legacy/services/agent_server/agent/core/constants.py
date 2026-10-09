from __future__ import annotations

SKILL_MOUNT_DIR = "/skills"

SANDBOX_NAME_PREFIX = "game-"
SANDBOX_TAG_THREAD = "aigame-thread"

AUTH_VERIFY_TIMEOUT_SECONDS = 10
SANDBOX_DEFAULT_EXEC_TIMEOUT_SECONDS = 30 * 60

PUBLISH_SINGLE_GAME_PATH = "/api/v1/internal/games/single/publish"
PUBLISH_TIMEOUT_SECONDS = 120

AUTO_SNAPSHOT_PATH = "/api/v1/internal/sessions"
AUTO_SNAPSHOT_TIMEOUT_SECONDS = 30

# 用户体系尚未落地：发布链路先用固定用户，待鉴权就绪后替换为真实身份
MOCK_USER_ID = "local-dev"
