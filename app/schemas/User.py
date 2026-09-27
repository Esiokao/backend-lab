from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# 建立 User 時，API 會接收這些資料


class UserCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


# API 回傳 User 時，只回傳公開資訊，不回傳密碼
class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    # 允許 Pydantic 直接讀取 SQLAlchemy ORM object
    model_config = ConfigDict(from_attributes=True)


class UserUpdate(BaseModel):
    name: str
    email: str


class UserPatch(BaseModel):
    # Both fields are optional because PATCH only updates provided fields.
    name: Optional[str] = None
    email: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
