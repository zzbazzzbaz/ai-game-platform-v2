"""跨模块常量（业务模块禁止新增模块级常量）。"""

# 平台元数据库 schema
PLATFORM_SCHEMA = "platform"

# 沙盒内路径（与 sandbox/image 镜像、apps/agent 契约同步）
SANDBOX_WORK_ROOT = "/workspace/work"
SANDBOX_INPUT_ROOT = "/workspace/input"
SANDBOX_NOVNC_PORT = 9000
GAME_SERVER_PORT = 3000

# 沙盒内游戏服务命令（保活）
# 注意：pgrep 的 pattern 用 `[d]ev.mjs` 转义，避免匹配到执行本脚本的 bash 自身。
GAME_SERVER_ENSURE_COMMAND = "\n".join([
    f"cd {SANDBOX_WORK_ROOT}",
    "mkdir -p .runtime",
    'if ! pgrep -f "[d]ev.mjs" >/dev/null; then',
    "  nohup npm run dev > .runtime/server.log 2>&1 &",
    "  sleep 4",
    "fi",
    "tail -n 20 .runtime/server.log 2>/dev/null || true",
])

# 资源命名（sid = game_id 去横线；命名只由 game_id 推导）
GAME_DB_PREFIX = "game_"
GAME_DB_ROLE_SUFFIX = "_rw"

# 内部接口
INTERNAL_TOKEN_HEADER = "X-Internal-Token"

# 认证
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"
JWT_ALGORITHM = "RS256"
MAX_PASSWORD_BYTES = 72
MIN_PASSWORD_LENGTH = 8

# 版本状态
VERSION_STATUS_DEPLOYED = "deployed"

# 游戏 / 会话状态
STATUS_ACTIVE = "active"
STATUS_DISABLED = "disabled"

# 文件块
FILE_CHUNK_SIZE = 256 * 1024

# CloudRun 发布（M6）
TCB_UPLOAD_TIMEOUT_SECONDS = 300
TCB_BUSY_RETRY_COUNT = 12
TCB_BUSY_RETRY_INTERVAL_SECONDS = 30
TCB_READY_TIMEOUT_SECONDS = 900
TCB_READY_INTERVAL_SECONDS = 10
TCB_HEALTH_RETRY_COUNT = 80
TCB_HEALTH_INTERVAL_SECONDS = 15
# 云托管服务名上限 36 字符：`game-{game_id}` 超限，改 `g-{sid}`（34 字符，仍仅由 game_id 派生）
TCB_SERVER_NAME_PREFIX = "g-"
PUBLISH_BUILD_TIMEOUT_SECONDS = 300
PUBLISH_EXCLUDED_TOP = ("node_modules", "dist", ".runtime", "versions", "input")
PUBLISH_TEXT_SUFFIXES = (".js", ".mjs", ".json", ".html", ".css", ".md", ".txt", ".yml", ".yaml")
PUBLISH_FORBIDDEN_PATTERNS = (
    "postgresql://",
    "postgres://",
    "127.0.0.1",
    "http://localhost",
    "https://localhost",
)
VERSION_STATUS_DEPLOYING = "deploying"
VERSION_STATUS_FAILED = "failed"
