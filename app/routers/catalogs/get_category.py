from fastapi import HTTPException
from sqlalchemy import select

from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Category
from app.schemas.Category import CategoryResponse

router = SizeLimitedAPIRouter(prefix="/categories")


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(category_id: int, db: DbSession):
    category = db.scalar(select(Category).where(Category.id == category_id))
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    return category
