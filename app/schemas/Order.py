from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class OrderItemCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=100)


class OrderCreate(BaseModel):
    # 建立訂單必須指定商品明細；同一商品重複出現會被拒絕（400）。
    items: list[OrderItemCreate] = Field(min_length=1)


class OrderItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    product_id: int
    quantity: int
    unit_price: Decimal


class OrderResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    status: str
    created_at: datetime
    items: list[OrderItemResponse]
    paid_at: datetime | None


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    message: str
    order: OrderResponse
