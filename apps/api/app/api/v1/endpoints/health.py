from fastapi import APIRouter

from app.api.schemas.health import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """存活探针：compose healthcheck 与 CI 公网健康检查都用它。"""
    return HealthResponse(ok=True)
