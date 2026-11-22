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

# 资源上传（前端 → COS games/{game_id}/input/{asset_id}/{filename}）
ASSET_FILENAME_MAX_BYTES = 200
ASSET_FILENAME_FALLBACK = "file"
ASSET_ALLOWED_CONTENT_TYPE_PREFIXES = ("image/", "audio/", "video/", "text/")
ASSET_ALLOWED_CONTENT_TYPES = frozenset(
    {
        "application/json",
        "application/pdf",
        "application/zip",
        "application/octet-stream",
    }
)
ASSET_DENIED_EXTENSIONS = frozenset(
    {".sh", ".bash", ".exe", ".dll", ".so", ".dylib", ".bat", ".cmd", ".ps1"}
)
ASSET_UNSAFE_FILENAME_CHARS = frozenset('/\\:*?"<>|`\'')

# CloudRun 发布（M6）
# 发布任务在 API 进程内异步执行：同一游戏由 PG 咨询锁 + deploying 版本互斥。
PUBLISH_EXECUTOR_WORKERS = 4
# 单个发布任务的最长存活时间：构建 300s + 就绪 900s + 健康探测 1200s + 排队余量。
# 超过该时长仍卡在 deploying 视为进程异常中断，允许被下一次发布回收。
PUBLISH_JOB_TTL_SECONDS = 4500
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

# 体验版派生（按钮触发：复制当前项目 → 新建独立游戏/会话/数据库）
DEMO_NAME_SUFFIX = " · 体验版"
DEMO_THREAD_TITLE = "体验版生成"
# 复制工作区时排除的顶层目录：与发布包保持一致（依赖、构建产物、运行时日志、版本包、上传原件）
DEMO_COPY_EXCLUDED_TOP = PUBLISH_EXCLUDED_TOP
DEMO_KICKOFF_TEMPLATE = """【体验版派生任务】
这个项目是从《{parent_name}》完整复制出来的独立项目（新游戏、新数据库），不是主游戏的分支。
请把它改造成可单独发布的试玩版：

1. 先读 src/ 和 shared/，弄清关卡/流程结构。保留第 1 关；如果第 1 关明显不适合试玩，选最合适的一关，并在回复里说明理由。
2. 只保留这一关的完整流程：开始 → 游玩 → 结束。移除后续关卡入口、关卡选择、解锁/存档继承、与试玩无关的系统；不要留下能进入后续内容的隐藏入口。
3. 在试玩结束处加「体验结束」页，放「玩完整版」按钮。{cta}
4. 游戏内标题改为「{demo_name}」，或保留原名并标注「体验版」。
5. 如果关卡内容依赖数据库，给体验版补一份最小种子数据；你只能看到本项目的空库。
6. 平台维护文件不要改；完成后执行一次 npm run build，失败最多修 2 次。
7. 不要发布。完成后告诉我：保留了哪一关、删了什么、完整版入口在哪，等我预览。
"""
