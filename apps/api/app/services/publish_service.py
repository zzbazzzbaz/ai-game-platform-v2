"""发布（M6）：受理 → 沙盒校验 → 打包 → COS 版本包 → CloudRun 部署 → 版本落库。

发布是**异步**的：`start_publish` 只在事务内抢占发布权并插入 deploying 版本，
部署由 API 进程内 `DaemonExecutor` 执行；调用方立即拿到版本号。
同一游戏同一时间只允许一个在途发布（PG 咨询锁 + deploying 状态行）。
"""

import io
import logging
import tarfile
import uuid
import zipfile
from functools import partial
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.core.constants import (
    GAME_SERVER_ENSURE_COMMAND,
    GAME_SERVER_PORT,
    PUBLISH_BUILD_TIMEOUT_SECONDS,
    PUBLISH_EXCLUDED_TOP,
    PUBLISH_FORBIDDEN_PATTERNS,
    PUBLISH_TEXT_SUFFIXES,
    TCB_SERVER_NAME_PREFIX,
    VERSION_STATUS_DEPLOYING,
)
from app.core.exceptions import (
    ConflictError,
    NotFoundError,
    UpstreamError,
    ValidationError,
)
from app.core.naming import game_sid
from app.core.tasks import DaemonExecutor
from app.gateways.ags import AgsGateway
from app.gateways.cos import CosGateway
from app.gateways.pg_admin import PgAdminGateway
from app.gateways.tcb import TcbGateway
from app.models.game import Game
from app.models.thread import GameThread
from app.models.version import GameVersion
from app.repositories.game_repository import game_repository
from app.repositories.thread_repository import thread_repository
from app.repositories.version_repository import version_repository

logger = logging.getLogger(__name__)


def _collect_workspace(*, game_id: str, cos: CosGateway) -> dict[str, bytes]:
    """从 COS 收集工作区（排除 node_modules/dist/.runtime/versions/input）。"""
    prefix = cos.game_prefix(game_id)
    files: dict[str, bytes] = {}
    for key in cos.list_keys(prefix):
        rel = key[len(prefix) :]
        if not rel or rel.endswith("/"):
            continue
        if rel.split("/", 1)[0] in PUBLISH_EXCLUDED_TOP:
            continue
        data = cos.get_bytes(key)
        if data is None:
            raise UpstreamError(f"工作区文件读取失败：{rel}")
        files[rel] = data
    if "package.json" not in files:
        raise ValidationError("工作区缺少 package.json，无法发布")
    return files


def _validate_sources(files: dict[str, bytes]) -> None:
    """拒绝硬编码连接串 / 本地地址。"""
    bad: list[str] = []
    for rel, data in files.items():
        if not rel.lower().endswith(PUBLISH_TEXT_SUFFIXES):
            continue
        text = data.decode("utf-8", errors="ignore").lower()
        for pattern in PUBLISH_FORBIDDEN_PATTERNS:
            if pattern in text:
                bad.append(f"{rel}（含 {pattern}）")
                break
    if bad:
        raise ValidationError("源码包含硬编码连接串/本地地址，禁止发布：" + "；".join(bad[:5]))


def _build_zip(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for rel in sorted(files):
            zf.writestr(rel, files[rel])
    return buf.getvalue()


def _build_tar(files: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        for rel in sorted(files):
            data = files[rel]
            info = tarfile.TarInfo(name=rel)
            info.size = len(data)
            tf.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def _verify_in_sandbox(*, sandbox_id: str | None, ags: AgsGateway) -> None:
    """有沙盒则做真实构建与健康校验；沙盒不可用则跳过（Dockerfile 会再构建）。"""
    if not sandbox_id or ags.connect(sandbox_id) is None:
        return
    ags.run(sandbox_id, GAME_SERVER_ENSURE_COMMAND, timeout=180)
    code, out, err = ags.run(
        sandbox_id,
        "cd /workspace/work && npm run build",
        timeout=PUBLISH_BUILD_TIMEOUT_SECONDS,
    )
    if code != 0:
        raise ValidationError(f"发布前构建失败：{(err or out)[-300:]}")
    code, _, _ = ags.run(sandbox_id, "curl -s -m 10 http://localhost:3000/api/health", timeout=30)
    if code != 0:
        raise ValidationError("游戏服务健康检查未通过，请先确认预览可用")


def resolve_thread(*, thread_id: uuid.UUID, session: Session) -> tuple[GameThread, Game]:
    thread = thread_repository.get(session, thread_id)
    if thread is None:
        raise NotFoundError("会话不存在")
    game = game_repository.get(session, thread.game_id)
    if game is None:
        raise NotFoundError("游戏不存在")
    return thread, game


def resolve_source_thread(
    *, game_id: uuid.UUID, thread_id: uuid.UUID | None, session: Session
) -> GameThread:
    """发布来源会话：显式传入则校验归属，否则取本游戏最近会话。"""
    if thread_id is not None:
        thread = thread_repository.get(session, thread_id)
        if thread is None or thread.game_id != game_id:
            raise ValidationError("会话不属于该游戏")
        return thread
    threads = thread_repository.list_by_game(session, game_id)
    if not threads:
        raise ValidationError("请先创建会话再发布")
    return threads[0]


def start_publish(
    *,
    game_id: uuid.UUID,
    source_thread_id: uuid.UUID,
    name: str,
    session: Session,
) -> GameVersion:
    """受理发布：抢占本游戏发布权，插入 deploying 版本后立即返回。"""
    if not version_repository.acquire_publish_lock(session, game_id=game_id):
        session.rollback()
        raise ConflictError("发布请求正在处理中，请稍后重试")

    version_repository.fail_stale_for_game(session, game_id=game_id)
    active = version_repository.active_for_game(session, game_id=game_id)
    if active is not None:
        active_seq = active.seq
        session.rollback()
        raise ConflictError(f"已有发布正在进行（版本 #{active_seq}），请等待完成后再试")

    seq = version_repository.next_seq(session, game_id)
    return version_repository.create(
        session,
        game_id=game_id,
        seq=seq,
        source_thread_id=source_thread_id,
        note=name.strip(),
    )


def submit_publish(
    *,
    executor: DaemonExecutor,
    version_id: uuid.UUID,
    session_factory: sessionmaker[Session],
    cos: CosGateway,
    tcb: TcbGateway,
    ags: AgsGateway,
    pg_admin: PgAdminGateway,
) -> None:
    """把已受理的版本提交给进程内执行器。"""
    try:
        executor.submit(
            partial(
                execute_publish,
                version_id=version_id,
                session_factory=session_factory,
                cos=cos,
                tcb=tcb,
                ags=ags,
                pg_admin=pg_admin,
            )
        )
    except Exception as e:
        logger.exception("提交发布任务失败：version_id=%s", version_id)
        with session_factory() as session:
            version_repository.mark_failed(session, version_id)
        raise UpstreamError("发布任务提交失败，请重试") from e


def execute_publish(
    *,
    version_id: uuid.UUID,
    session_factory: sessionmaker[Session],
    cos: CosGateway,
    tcb: TcbGateway,
    ags: AgsGateway,
    pg_admin: PgAdminGateway,
) -> None:
    """后台执行一次发布；任何异常都落为 failed，不让线程静默死掉。"""
    with session_factory() as session:
        version = version_repository.get(session, version_id)
        if version is None or version.status != VERSION_STATUS_DEPLOYING:
            return
        game = game_repository.get(session, version.game_id)
        if game is None:
            version_repository.mark_failed(session, version_id)
            return
        game_id = game.game_id
        sandbox_id = game.sandbox_id
        seq = version.seq

    try:
        _verify_in_sandbox(sandbox_id=sandbox_id, ags=ags)
        files = _collect_workspace(game_id=str(game_id), cos=cos)
        _validate_sources(files)
        zip_bytes = _build_zip(files)
        tar_bytes = _build_tar(files)

        cos.put_bytes(cos.version_key(str(game_id), seq), tar_bytes)
        server_name = f"{TCB_SERVER_NAME_PREFIX}{game_sid(str(game_id))}"
        previous_deploy_time = tcb.get_latest_deploy_time(server_name=server_name)
        deploy = tcb.deploy_package(
            server_name=server_name,
            zip_bytes=zip_bytes,
            env_params={
                "DATABASE_URL": pg_admin.game_database_url(str(game_id)),
                "PORT": str(GAME_SERVER_PORT),
                "NODE_ENV": "production",
            },
            port=GAME_SERVER_PORT,
        )
        domain_url = tcb.wait_ready(
            server_name=server_name, previous_deploy_time=previous_deploy_time
        )
        tcb.probe_health(domain_url)
    except Exception:
        logger.exception("发布失败：version_id=%s game_id=%s", version_id, game_id)
        with session_factory() as session:
            version_repository.mark_failed(session, version_id)
        return

    with session_factory() as session:
        version_repository.mark_deployed(
            session, version_id, revision=deploy.get("package_version")
        )
        game = game_repository.get(session, game_id)
        if game is not None and not game.public_url:
            game_repository.set_public_url(session, game_id=game_id, public_url=domain_url)
    logger.info(
        "发布成功：version_id=%s game_id=%s seq=%s url=%s",
        version_id,
        game_id,
        seq,
        domain_url,
    )


def publish_result(*, game: Game, version: GameVersion) -> dict[str, Any]:
    return {
        "game_id": game.game_id,
        "version_id": version.version_id,
        "seq": version.seq,
        "status": version.status,
        "public_url": game.public_url,
    }


def get_publish_status(*, thread_id: uuid.UUID, session: Session) -> dict[str, Any]:
    _thread, game = resolve_thread(thread_id=thread_id, session=session)
    version_repository.reap_stale(session, game_id=game.game_id)
    version = version_repository.latest_for_game(session, game.game_id)
    return {
        "game_id": game.game_id,
        "public_url": game.public_url,
        "deploying": version is not None and version.status == VERSION_STATUS_DEPLOYING,
        "version": version,
    }
