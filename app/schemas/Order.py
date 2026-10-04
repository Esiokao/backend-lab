from pydantic import BaseModel


class OrderCreate(BaseModel):
    # 目前 Order 沒有其他由 client 提供的欄位
    # user_id 由 JWT 的 current_user.id 決定
    pass
