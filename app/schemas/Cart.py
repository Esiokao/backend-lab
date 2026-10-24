from decimal import Decimal

from pydantic import BaseModel, Field


class CartItemAdd(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=100)


class CartItemUpdate(BaseModel):
    quantity: int = Field(gt=0, le=100)


class CartItemResponse(BaseModel):
    product_id: int
    product_name: str
    quantity: int
    unit_price: Decimal
    subtotal: Decimal
    # 目前庫存：前端以此判斷可否勾選結帳（quantity > stock → 不可選）。
    stock: int


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    total: Decimal


class CartCheckout(BaseModel):
    # 只結帳 selected 商品（前端勾選）；缺省 = 整台車。
    product_ids: list[int] | None = Field(default=None, min_length=1)
