from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import Settings
from app.core.database import create_all, create_db_engine, create_session_factory
from app.gateways.minio import MinioGateway
from app.gateways.modal import ModalGateway


def build_lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(application: FastAPI) -> AsyncGenerator[None]:
        engine = create_db_engine(settings.sqlalchemy_database_url)
        create_all(engine)
        application.state.session_factory = create_session_factory(engine)
        minio = MinioGateway(
            endpoint_url=settings.s3_endpoint_url,
            bucket=settings.s3_bucket,
            path_style=settings.s3_path_style,
            access_key=settings.s3_access_key,
            secret_key=settings.s3_secret_key,
        )
        minio.ensure_bucket()
        application.state.minio = minio
        application.state.modal = ModalGateway(
            app_name=settings.modal_app,
            image_tag=settings.modal_image_tag,
            idle_timeout=settings.modal_idle_timeout_seconds,
            timeout=settings.modal_timeout_seconds,
        )
        try:
            yield
        finally:
            engine.dispose()

    return lifespan
