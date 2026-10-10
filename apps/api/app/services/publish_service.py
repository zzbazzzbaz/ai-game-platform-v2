"""发布（M6）：沙盒校验 → 打包 → COS 版本包 → CloudRun 部署 → 版本落库（规格 §7.1/§7.4）。

调用链已实测（`test/infra/cloudbase/api_deploy_verify.py`）：tcb:DescribeCloudBaseBuildService
→ PUT 源码 zip → tcbr:CreateCloudRunServer / UpdateCloudRunServer → 轮询默认域名 → 健康检查。
"""

import io
import tarfile
import uuid
import zipfile

from sqlalchemy.orm import Session

from app.core.constants import (
    GAME_SERVER_ENSURE_COMMAND,
    PUBLISH_BUILD_TIMEOUT_SECONDS,
    PUBLISH_EXCLUDED_TOP,
    PUBLISH_FORBIDDEN_PATTERNS,
    PUBLISH_TEXT_SUFFIXES,
    TCB_SERVER_NAME_PREFIX,
)
from app.core.exceptions import NotFoundError, UpstreamError, ValidationError
from app.core.naming import game_sid
from app.gateways.ags import AgsGateway
from app.gateways.cos import CosGateway
from app.gateways.pg_admin import PgAdminGateway
from app.gateways.tcb import TcbGateway
from app.repositories.game_repository import game_repository
from app.repositories.thread_repository import thread_repository
from app.repositories.version_repository import version_repository


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
    """拒绝硬编码连接串 / 本地地址（规格 §7.4）。"""
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
    """有沙盒则做真实构建与健康校验（规格 §7.4）；沙盒不可用则跳过（Dockerfile 会再构建）。"""
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


def publish_game(
    *,
    thread_id: uuid.UUID,
    name: str,
    session: Session,
    cos: CosGateway,
    tcb: TcbGateway,
    ags: AgsGateway,
    pg_admin: PgAdminGateway,
) -> dict:
    thread = thread_repository.get(session, thread_id)
    if thread is None:
        raise NotFoundError("会话不存在")
    game = game_repository.get(session, thread.game_id)
    if game is None:
        raise NotFoundError("游戏不存在")
    game_id = str(game.game_id)

    _verify_in_sandbox(sandbox_id=game.sandbox_id, ags=ags)
    files = _collect_workspace(game_id=game_id, cos=cos)
    _validate_sources(files)
    zip_bytes = _build_zip(files)
    tar_bytes = _build_tar(files)

    seq = version_repository.next_seq(session, game.game_id)
    version = version_repository.create(
        session,
        game_id=game.game_id,
        seq=seq,
        source_thread_id=thread.thread_id,
        note=name.strip(),
    )
    version_repository.mark_deploying(session, version.version_id)

    try:
        cos.put_bytes(cos.version_key(game_id, seq), tar_bytes)
        server_name = f"{TCB_SERVER_NAME_PREFIX}{game_sid(game_id)}"
        previous_deploy_time = tcb.get_latest_deploy_time(server_name=server_name)
        deploy = tcb.deploy_package(
            server_name=server_name,
            zip_bytes=zip_bytes,
            env_params={
                "DATABASE_URL": pg_admin.game_database_url(game_id),
                "PORT": "3000",
                "NODE_ENV": "production",
            },
            port=3000,
        )
        domain_url = tcb.wait_ready(
            server_name=server_name, previous_deploy_time=previous_deploy_time
        )
        tcb.probe_health(domain_url)
    except Exception:
        version_repository.mark_failed(session, version.version_id)
        raise

    public_url = domain_url
    version_repository.mark_deployed(
        session, version.version_id, revision=deploy.get("package_version")
    )
    if not game.public_url:
        game_repository.set_public_url(session, game_id=game.game_id, public_url=public_url)
    return {"game_id": game.game_id, "public_url": public_url, "seq": seq}
