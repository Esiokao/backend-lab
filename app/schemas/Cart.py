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


class CartResponse(BaseModel):
    items: list[CartItemResponse]
    total: Decimal
