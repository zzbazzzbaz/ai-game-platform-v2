from fastapi import APIRouter
from fastapi.responses import Response, StreamingResponse

from app.api.dependencies import MinioDep
from app.core.constants import HTML_MEDIA_TYPE
from app.services import game_service

router = APIRouter(prefix="/games", tags=["games"])


@router.get("/{thread_id}/index.html")
def play_published(thread_id: str, minio: MinioDep) -> Response:
    """按 thread_id 播放最新发布的单人游戏（与 MinIO 公网链接等价，同源备选）。"""
    stream = game_service.open_game_stream(minio=minio, thread_id=thread_id)
    return StreamingResponse(stream, media_type=HTML_MEDIA_TYPE)
