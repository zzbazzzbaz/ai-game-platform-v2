"""跨模块常量（与 apps/api/app/core/constants.py、sandbox/image 镜像契约同步）。"""

# 沙盒内路径
SKILLS_MOUNT_DIR = "/opt/skills"

# 内部接口（契约权威：apps/api/app/api/schemas/internal.py）
INTERNAL_TOKEN_HEADER = "X-Internal-Token"
ENSURE_SESSION_PATH = "/api/v1/internal/sessions/ensure"
PROVISION_DATABASE_PATH = "/api/v1/internal/db/provision"
PUBLISH_GAME_PATH = "/api/v1/internal/games/publish"
PUBLISH_STATUS_PATH = "/api/v1/internal/games/publish/status"

# 超时
ENSURE_TIMEOUT_SECONDS = 900
INTERNAL_TIMEOUT_SECONDS = 120
# 发布是异步受理：启动与状态查询都只做 DB 读写，快速返回；部署耗时不在此等待。
PUBLISH_START_TIMEOUT_SECONDS = 60
PUBLISH_STATUS_TIMEOUT_SECONDS = 60
SANDBOX_DEFAULT_EXEC_TIMEOUT_SECONDS = 30 * 60
