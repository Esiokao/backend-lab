from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None


class CategoryPatch(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None


class CategoryReorderRequest(BaseModel):
    """批次重排：完整分類 id 清單，依新順序排列。"""

    category_ids: list[int] = Field(min_length=1)


class CategoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    sort_order: int
    created_at: datetime


class CategoryListResponse(BaseModel):
    """分頁包裝：admin 管理頁的搜尋/分頁；店面取全量用大 page_size。"""

    items: list[CategoryResponse]
    total: int
    page: int
    page_size: int
