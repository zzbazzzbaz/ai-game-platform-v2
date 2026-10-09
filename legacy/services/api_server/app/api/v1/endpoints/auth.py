from fastapi import APIRouter

from app.api.schemas.auth import LoginBody, LoginResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(body: LoginBody) -> LoginResponse:
    token, ttl = auth_service.login(body.user_id)
    return LoginResponse(token=token, expires_in=ttl)
