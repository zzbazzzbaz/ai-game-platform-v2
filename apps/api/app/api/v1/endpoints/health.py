from fastapi import APIRouter

from app.api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """存活探针（compose healthcheck / CI 健康检查）。"""
    return HealthResponse(ok=True)
