from fastapi import Query
from sqlalchemy import func, select

from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Category
from app.schemas.Category import CategoryListResponse, CategoryResponse

router = SizeLimitedAPIRouter(prefix="/categories")


@router.get("", response_model=CategoryListResponse)
def list_categories(
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=100),
    q: str | None = Query(default=None, max_length=100),
):
    # 公開端點：店面導覷列取全量（預設 page_size=100）；admin 管理頁帶 q/分頁。
    base = select(Category)
    if q:
        base = base.where(Category.name.ilike(f"%{q}%"))

    total = db.scalar(select(func.count()).select_from(base.subquery()))
    items = db.scalars(
        base.order_by(Category.id).offset((page - 1) * page_size).limit(page_size)
    ).all()

    return {
        "items": [CategoryResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }
