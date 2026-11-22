import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager

from fastapi import FastAPI
from sqlalchemy import text

import app.models  # noqa: F401  确保建表模型已注册
from app.core.config import Settings
from app.core.constants import PLATFORM_SCHEMA, PUBLISH_EXECUTOR_WORKERS
from app.core.database import create_all, create_db_engine, create_session_factory
from app.core.tasks import DaemonExecutor
from app.gateways.ags import AgsGateway
from app.gateways.cos import CosGateway
from app.gateways.pg_admin import PgAdminGateway
from app.gateways.tcb import TcbGateway
from app.repositories.version_repository import version_repository

logger = logging.getLogger(__name__)


def build_lifespan(settings: Settings) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        engine = create_db_engine(settings.sqlalchemy_database_url)
        with engine.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{PLATFORM_SCHEMA}"'))
        create_all(engine)
        application.state.session_factory = create_session_factory(engine)
        # 发布执行器在进程内，重启后无法续跑：残留的 deploying 一律判失败，允许用户重新发布。
        with application.state.session_factory() as session:
            interrupted = version_repository.fail_all_deploying(session)
        if interrupted:
            logger.warning("启动对账：%s 个未完成发布已标记为失败", interrupted)
        application.state.ags = AgsGateway(
            domain=settings.e2b_domain,
            api_key=settings.e2b_api_key,
            template=settings.ags_template,
            timeout_seconds=settings.sandbox_timeout_seconds,
        )
        application.state.cos = CosGateway(
            secret_id=settings.cos_secret_id,
            secret_key=settings.cos_secret_key,
            region=settings.cos_region,
            bucket=settings.cos_bucket,
            games_prefix=settings.cos_games_prefix,
        )
        application.state.pg_admin = PgAdminGateway(
            host=settings.pg_admin_host,
            port=settings.pg_admin_port,
            user=settings.pg_admin_user,
            password=settings.pg_admin_password,
            admin_db=settings.pg_admin_db,
            game_db_host=settings.game_db_host,
            game_db_port=settings.game_db_port,
            sslmode=settings.game_db_sslmode,
        )
        application.state.tcb = TcbGateway(
            secret_id=settings.tencent_secret_id,
            secret_key=settings.tencent_secret_key,
            env_id=settings.tcb_env_id,
            region=settings.tcb_region,
        )
        application.state.publish_executor = DaemonExecutor(
            max_workers=PUBLISH_EXECUTOR_WORKERS,
            thread_name_prefix="publish",
        )
        try:
            yield
        finally:
            application.state.publish_executor.shutdown()
            engine.dispose()

    return lifespan
