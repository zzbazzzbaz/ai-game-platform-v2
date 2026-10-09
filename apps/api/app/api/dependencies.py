import hmac
import uuid
from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.constants import INTERNAL_TOKEN_HEADER
from app.core.exceptions import ValidationError
from app.core.security import decode_access_token
from app.gateways.ags import AgsGateway
from app.gateways.cos import CosGateway
from app.gateways.pg_admin import PgAdminGateway
from app.gateways.tcb import TcbGateway


def get_session(request: Request) -> Iterator[Session]:
    with request.app.state.session_factory() as session:
        try:
            yield session
        except Exception:
            session.rollback()
            raise


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_ags(request: Request) -> AgsGateway:
    return request.app.state.ags


def get_cos(request: Request) -> CosGateway:
    return request.app.state.cos


def get_pg_admin(request: Request) -> PgAdminGateway:
    return request.app.state.pg_admin


def get_tcb(request: Request) -> TcbGateway:
    return request.app.state.tcb


def _bearer(request: Request) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


def require_user(request: Request) -> uuid.UUID:
    token = _bearer(request)
    if token is None:
        raise HTTPException(status_code=401, detail="缺少登录凭证")
    try:
        return uuid.UUID(decode_access_token(token))
    except (ValidationError, ValueError) as e:
        raise HTTPException(status_code=401, detail="登录已失效，请重新登录") from e


def require_internal(
    request: Request,
    x_internal_token: str = Header(default="", alias=INTERNAL_TOKEN_HEADER),
) -> None:
    settings: Settings = request.app.state.settings
    if not hmac.compare_digest(x_internal_token, settings.internal_token):
        raise HTTPException(status_code=403, detail="内部鉴权失败")


SessionDep = Annotated[Session, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
AgsDep = Annotated[AgsGateway, Depends(get_ags)]
CosDep = Annotated[CosGateway, Depends(get_cos)]
PgAdminDep = Annotated[PgAdminGateway, Depends(get_pg_admin)]
TcbDep = Annotated[TcbGateway, Depends(get_tcb)]
UserIdDep = Annotated[uuid.UUID, Depends(require_user)]
InternalDep = Annotated[None, Depends(require_internal)]
