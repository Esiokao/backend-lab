# app/schemas/Auth.py

from pydantic import BaseModel, EmailStr, Field


class UserLogin(BaseModel):
    # 使用者登入時，API 接收的 email。
    email: EmailStr

    # 密碼長度限制。
    password: str = Field(min_length=8, max_length=128)

    # 「Keep me signed in」：勾選時 session 與 cookie 用 7 天 TTL（預設 30 分鐘）。
    remember_me: bool = False


class LoginRequest(BaseModel):
    email: str
    password: str


class AccessTokenPayload(BaseModel):
    # JWT 的 subject，代表 User ID。
    sub: str = Field(pattern=r"^[0-9]+$")

    # JWT expiration timestamp。
    exp: int
