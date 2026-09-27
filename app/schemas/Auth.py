from pydantic import BaseModel


# 使用者登入時，API 接收的資料
class LoginRequest(BaseModel):
    email: str
    password: str
