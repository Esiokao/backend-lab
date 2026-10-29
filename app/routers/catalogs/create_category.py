from fastapi import Depends, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.core.request_size import SizeLimitedAPIRouter
from app.database import get_db
from app.models import Category, User
from app.schemas.Category import CategoryCreate, CategoryResponse

router = SizeLimitedAPIRouter(prefix="/categories")


@router.post("", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    category = Category(name=payload.name, description=payload.description)
    db.add(category)
    db.commit()
    db.refresh(category)
    return category
