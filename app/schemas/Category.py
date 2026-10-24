from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class CategoryPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    created_at: datetime


class CategoryListResponse(BaseModel):
    """分頁包裝：admin 管理頁的搜尋/分頁；店面取全量用大 page_size。"""

    items: list[CategoryResponse]
    total: int
    page: int
    page_size: int
