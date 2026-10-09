"""跨模块常量（业务模块禁止新增模块级常量）。"""

# 平台元数据库 schema
PLATFORM_SCHEMA = "platform"

# 沙盒内路径（与 infra/sandbox/init.sh 契约同步）
SANDBOX_WORK_ROOT = "/workspace/work"
SANDBOX_INPUT_ROOT = "/workspace/input"
SANDBOX_DEPS_ROOT = "/opt/deps"
SANDBOX_SKILLS_ROOT = "/opt/skills"
SANDBOX_INIT_MARKER = "/opt/.aigame-init-done"
SANDBOX_SKILLS_TMP = "/tmp/skills.tar.gz"
SANDBOX_NOVNC_PORT = 9000
SANDBOX_CDP_PORT = 9000
GAME_SERVER_PORT = 3000

# 沙盒内游戏服务命令（保活 / 重启）
# 注意：pgrep/pkill 的 pattern 用 `[s]erver` 转义，避免匹配到执行本脚本的 bash 自身。
GAME_SERVER_ENSURE_COMMAND = "\n".join(
    [
        f"cd {SANDBOX_WORK_ROOT}",
        "mkdir -p .runtime",
        'if ! pgrep -f "[d]ev.mjs" >/dev/null; then',
        "  nohup npm run dev > .runtime/server.log 2>&1 &",
        "  sleep 4",
        "fi",
        "tail -n 20 .runtime/server.log 2>/dev/null || true",
    ]
)
GAME_SERVER_RESTART_COMMAND = "\n".join(
    [
        f"cd {SANDBOX_WORK_ROOT}",
        "mkdir -p .runtime",
        'pkill -f "[d]ev.mjs" || true',
        'pkill -f "[s]erver/index.js" || true',
        "sleep 1",
        "nohup npm run dev > .runtime/server.log 2>&1 &",
        "sleep 4",
        "tail -n 80 .runtime/server.log",
    ]
)

# COS 平台资产（infra/sandbox/publish_assets.py 发布）
COS_TEMPLATE_PREFIX = "game-template"
COS_SKILLS_ARCHIVE = "sandbox/skills.tar.gz"
COS_INIT_SCRIPT = "sandbox/init.sh"

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
