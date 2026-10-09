from pydantic import BaseModel


class LoginBody(BaseModel):
    user_id: str = ""


class LoginResponse(BaseModel):
    token: str
    expires_in: int


class VerifyResponse(BaseModel):
    user_id: str
