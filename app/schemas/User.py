from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, EmailStr, Field


def _clean_name(v: str) -> str:
    # 前後空白修剪；純空白（如 "   "）等於沒有名字，直接拒絕。
    v = v.strip()
    if not v:
        raise ValueError("name must not be blank")
    return v


# 共用：所有可寫入的 name 欄位一律 trim + 拒絕純空白，與前端 zod .trim() 同標準。
NameStr = Annotated[str, AfterValidator(_clean_name), Field(max_length=100)]

# 建立 User 時，API 會接收這些資料


class UserCreate(BaseModel):
    name: NameStr
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


# admin 管理介面更新使用者：可比一般管道多改 role，但不能改密碼
class AdminUserPatch(BaseModel):
    name: NameStr | None = None
    email: EmailStr | None = None
    role: Literal["user", "admin"] | None = None


# API 回傳 User 時，只回傳公開資訊，不回傳密碼
class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    role: str

    # 允許 Pydantic 直接讀取 SQLAlchemy ORM object
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    name: NameStr
    email: str


class UserPatch(BaseModel):
    # Both fields are optional because PATCH only updates provided fields.
    name: NameStr | None = None
    email: str | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
