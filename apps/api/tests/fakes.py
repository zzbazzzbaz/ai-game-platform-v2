"""测试替身：假沙盒 / 假 COS / 假 PG 管理网关。

全部只做内存记录，不触达 AGS、COS、游戏库；语义尽量贴近真实实现，
否则测试就测不到真正的分支（例如 connect 失败 → 新建）。
假网关继承真实网关，保证与 services 的参数类型一致（ty 严格检查）。
"""

import itertools
import time
import uuid
from dataclasses import dataclass
from typing import Any, ClassVar

from sqlalchemy.orm import Session, sessionmaker

from app.gateways.cos import CosGateway
from app.gateways.pg_admin import PgAdminGateway
from app.models.game import Game


class FakeSandboxNotFound(Exception):
    """模拟 e2b.SandboxNotFoundException。"""


@dataclass(frozen=True)
class FakeCommandResult:
    """`sandbox.commands.run(...)` 的返回值（AgsGateway.run 只读这三个字段）。"""

    exit_code: int
    stdout: str
    stderr: str


class _FakeCommands:
    """`sandbox.commands.run(...)` 的最小面。"""

    def __init__(self, sandbox: FakeSandbox) -> None:
        self._sandbox = sandbox

    def run(
        self, command: str, *, timeout: int | None = None, user: str | None = None
    ) -> FakeCommandResult:
        FakeSandbox.command_log.append((self._sandbox.sandbox_id, command))
        return FakeCommandResult(exit_code=0, stdout="", stderr="")


class FakeSandbox:
    """替换 `app.gateways.ags.Sandbox`。

    - `registered` 里的 id 视为存活；其余 `connect` 抛错（模拟被回收的实例）；
    - `create` 生成新 id，并睡眠 `create_delay` 秒——复现「创建要几秒」的竞态窗口；
    - 记录 create/commands 调用，供断言。
    """

    registered: ClassVar[set[str]] = set()
    created: ClassVar[list[str]] = []
    created_kwargs: ClassVar[list[dict[str, object]]] = []
    command_log: ClassVar[list[tuple[str, str]]] = []
    create_delay: ClassVar[float] = 0.0
    _ids: ClassVar[itertools.count[int]] = itertools.count(1)

    def __init__(self, sandbox_id: str) -> None:
        self.sandbox_id = sandbox_id

    @classmethod
    def reset(cls) -> None:
        cls.registered = set()
        cls.created = []
        cls.created_kwargs = []
        cls.command_log = []
        cls.create_delay = 0.0
        cls._ids = itertools.count(1)

    @classmethod
    def connect(cls, sandbox_id: str, **kwargs: object) -> FakeSandbox:
        if sandbox_id not in cls.registered:
            raise FakeSandboxNotFound(f"Paused sandbox {sandbox_id} not found")
        return cls(sandbox_id)

    @classmethod
    def create(cls, **kwargs: object) -> FakeSandbox:
        time.sleep(cls.create_delay)
        sandbox_id = f"sbx-{next(cls._ids)}"
        cls.registered.add(sandbox_id)
        cls.created.append(sandbox_id)
        cls.created_kwargs.append(kwargs)
        return cls(sandbox_id)

    @property
    def commands(self) -> _FakeCommands:
        return _FakeCommands(self)


class FakeCos(CosGateway):
    """内存 COS：记录前缀初始化、预签名与对象，供资源上传接口断言。"""

    def __init__(self) -> None:
        self._bucket = "fake-bucket"
        self._games_prefix = "games"
        self.ensured_prefixes: list[str] = []
        self.objects: dict[str, dict[str, Any]] = {}
        self.presigned: list[dict[str, Any]] = []
        self.deleted: list[str] = []

    def ensure_game_prefixes(self, game_id: object) -> None:
        self.ensured_prefixes.append(str(game_id))

    def presign_put(self, key: str, *, content_type: str, expires_seconds: int) -> str:
        self.presigned.append(
            {"key": key, "content_type": content_type, "expires_seconds": expires_seconds}
        )
        return f"https://fake-cos.example/{key}?signature=fake"

    def head_object(self, key: str) -> dict[str, Any] | None:
        return self.objects.get(key)

    def delete_object(self, key: str) -> None:
        self.deleted.append(key)
        self.objects.pop(key, None)

    def delete_prefix(self, prefix: str) -> int:
        keys = [key for key in self.objects if key.startswith(prefix)]
        for key in keys:
            self.delete_object(key)
        return len(keys)

    def list_objects(self, prefix: str) -> list[dict[str, Any]]:
        return [
            {"Key": key, **metadata}
            for key, metadata in self.objects.items()
            if key.startswith(prefix)
        ]

    def list_keys(self, prefix: str) -> list[str]:
        return [str(item["Key"]) for item in self.list_objects(prefix)]

    def add_object(
        self, key: str, *, size: int, content_type: str, last_modified: str | None = None
    ) -> None:
        self.objects[key] = {
            "Content-Length": str(size),
            "Content-Type": content_type,
            "Size": str(size),
            "LastModified": last_modified or "2026-11-08T00:00:00.000Z",
        }


class FakePgAdmin(PgAdminGateway):
    """game_database_url 返回可断言形状的假连接串。"""

    def __init__(self) -> None:
        self.requested: list[str] = []

    def game_database_url(self, game_id: str) -> str:
        self.requested.append(game_id)
        sid = game_id.replace("-", "")
        return f"postgresql://game_{sid}_rw:secret@game-db:5432/game_{sid}"


def set_game_sandbox(
    session_factory: sessionmaker[Session], game_id: uuid.UUID, sandbox_id: str | None
) -> None:
    """直接把 games.sandbox_id 写成指定值（模拟库里的历史值）。"""
    with session_factory() as session:
        game = session.get(Game, game_id)
        assert game is not None
        game.sandbox_id = sandbox_id
        session.commit()


def read_game_sandbox(session_factory: sessionmaker[Session], game_id: uuid.UUID) -> str | None:
    """读库里当前的 games.sandbox_id。"""
    with session_factory() as session:
        game = session.get(Game, game_id)
        assert game is not None
        return game.sandbox_id
