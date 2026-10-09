"""跨模块常量（与 apps/api/app/core/constants.py、infra/sandbox/init.sh 契约同步）。"""

# 沙盒内路径
SKILLS_MOUNT_DIR = "/opt/skills"
WORK_ROOT = "/workspace/work"
RUNTIME_DIR = "/workspace/work/.runtime"
SCREENSHOT_PATH = "/workspace/work/.runtime/screenshot.png"
NOVNC_PORT = 9000

# 内部接口（契约权威：apps/api/app/api/schemas/internal.py）
INTERNAL_TOKEN_HEADER = "X-Internal-Token"
ENSURE_SESSION_PATH = "/api/v1/internal/sessions/ensure"
PROVISION_DATABASE_PATH = "/api/v1/internal/db/provision"
RESTART_SERVER_PATH = "/api/v1/internal/sessions/{thread_id}/server/restart"
PUBLISH_GAME_PATH = "/api/v1/internal/games/publish"

# 超时
ENSURE_TIMEOUT_SECONDS = 900
INTERNAL_TIMEOUT_SECONDS = 120
PUBLISH_TIMEOUT_SECONDS = 600
SANDBOX_DEFAULT_EXEC_TIMEOUT_SECONDS = 30 * 60
