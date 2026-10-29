from fastapi import HTTPException

from app.core.dependencies import AdminUser
from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Category
from app.schemas.Category import CategoryPatch, CategoryResponse

router = SizeLimitedAPIRouter(prefix="/categories")


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    payload: CategoryPatch,
    db: DbSession,
    _: AdminUser,
):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(category, field, value)
    db.commit()
    db.refresh(category)
    return category
