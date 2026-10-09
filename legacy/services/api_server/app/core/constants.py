import re

WORK_ROOT = "/workspace/work"
INPUT_ROOT = "/workspace/input"
WORK_INDEX_FILE = "index.html"
WORK_DIST_INDEX = "dist/index.html"

SNAPSHOT_EXCLUDED_TOP = ("dist",)
SANDBOX_HASH_BATCH_SIZE = 200

GAME_TYPE_SINGLE = "single"

FILE_CHUNK_SIZE = 256 * 1024
STREAM_CHUNK_SIZE = 64 * 1024
RESTORE_CONCURRENCY = 8

SANDBOX_NAME_PREFIX = "game-"
SANDBOX_TAG_THREAD = "aigame-thread"
SANDBOX_IMAGE_NAME = "game-runner"
SANDBOX_READY_RETRIES = 10
SANDBOX_READY_INTERVAL_SECONDS = 3
SANDBOX_EXEC_TIMEOUT_SECONDS = 60

MAX_HTML_BYTES = 2 * 1024 * 1024
MAX_SCRIPT_BYTES = 2 * 1024 * 1024
MAX_INPUT_BYTES = 5 * 1024 * 1024

THREAD_ID_PATTERN = re.compile(
    r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
USER_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
FILENAME_PATTERN = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.\-]{0,127}$")

INPUT_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".txt", ".md", ".json", ".csv"}
)

HTML_MEDIA_TYPE = "text/html; charset=utf-8"
BINARY_MEDIA_TYPE = "application/octet-stream"
JSON_MEDIA_TYPE = "application/json"

# HTML 中必须内联的资源属性：{标签: (属性, ...)}
INLINE_RESOURCE_ATTRS = {
    "script": ("src",),
    "link": ("href",),
    "img": ("src",),
    "video": ("src", "poster"),
    "audio": ("src",),
    "source": ("src",),
}
INLINE_REF_PREFIXES = ("data:", "blob:", "#")
