from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    # v1 只存外部圖片 URL；上傳功能另開。
    image_url: str | None = None
    price: Decimal = Field(ge=0, decimal_places=2)
    stock: int = Field(default=0, ge=0)


class ProductPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    image_url: str | None = None
    price: Decimal | None = Field(default=None, ge=0, decimal_places=2)
    stock: int | None = Field(default=None, ge=0)


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    image_url: str | None
    price: Decimal
    stock: int
    created_at: datetime
    is_active: bool


class ProductRestockJobPayload(BaseModel):
    outbox_event_id: int = Field(gt=0)
    product_id: int = Field(gt=0)
