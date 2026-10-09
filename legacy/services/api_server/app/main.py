from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.errors import register_error_handlers
from app.api.v1.router import api_router
from app.core.config import Settings, get_settings
from app.lifespan import build_lifespan


def create_app(settings: Settings | None = None) -> FastAPI:
    resolved_settings = settings if settings is not None else get_settings()
    application = FastAPI(
        title="ai-game-api",
        version="0.1.0",
        lifespan=build_lifespan(resolved_settings),
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved_settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.state.settings = resolved_settings
    register_error_handlers(application)
    application.include_router(api_router, prefix="/api/v1")
    return application


app = create_app()
