from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class OrderCreate(BaseModel):
    # 建立訂單時必須指定商品。
    product_id: int = Field(gt=0)

    # 購買數量必須是正整數。
    quantity: int = Field(gt=0)


class OrderResponse(BaseModel):
    id: int
    user_id: int
    product_id: int
    quantity: int
    status: str
    created_at: datetime

    # 允許 Pydantic 從 SQLAlchemy Order model 讀取欄位。
    model_config = ConfigDict(from_attributes=True)
