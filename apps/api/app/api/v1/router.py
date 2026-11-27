from fastapi import APIRouter

from app.api.v1.endpoints import assets, auth, games, internal, internal_maps, maps, sessions

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(games.router)
api_router.include_router(maps.router)
api_router.include_router(assets.router)
api_router.include_router(sessions.router)
api_router.include_router(internal.router)
api_router.include_router(internal_maps.router)
