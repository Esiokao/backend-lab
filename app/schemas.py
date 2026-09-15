from pydantic import BaseModel, ConfigDict
from typing import Optional


class UserCreate(BaseModel):
    # POST /users 要求 client 提供的資料
    name: str
    email: str


class UserResponse(BaseModel):
    # 允許 Pydantic 從 SQLAlchemy ORM object
    # 的 attributes 讀取資料
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    
class UserUpdate(BaseModel):
    name: str
    email: str
    

class UserPatch(BaseModel):
    # Both fields are optional because PATCH only updates provided fields.
    name: Optional[str] = None
    email: Optional[str] = None
    
class OrderCreate(BaseModel):
    user_id: int
