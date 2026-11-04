from fastapi import status
from sqlalchemy import func, select

from app.core.dependencies import AdminUser
from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Category
from app.schemas.Category import CategoryCreate, CategoryResponse

router = SizeLimitedAPIRouter(prefix="/categories")


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: DbSession,
    _: AdminUser,
):
    # 新分類排到最後：sort_order = 目前最大值 + 1（空表則 0）。
    max_order = db.scalar(select(func.max(Category.sort_order)))
    category = Category(
        name=payload.name,
        description=payload.description,
        sort_order=(max_order or 0) + 1,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
