from typing import Any

from fastapi import APIRouter

from app.api.dependencies import SessionDep
from app.api.schemas.auth import AuthResponse, LoginBody, RefreshBody, RegisterBody
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=AuthResponse)
def register(body: RegisterBody, session: SessionDep) -> dict[str, Any]:
    return auth_service.register(username=body.username, password=body.password, session=session)


@router.post("/login", response_model=AuthResponse)
def login(body: LoginBody, session: SessionDep) -> dict[str, Any]:
    return auth_service.login(username=body.username, password=body.password, session=session)


@router.post("/refresh", response_model=AuthResponse)
def refresh(body: RefreshBody, session: SessionDep) -> dict[str, Any]:
    return auth_service.refresh(refresh_token=body.refresh_token, session=session)
