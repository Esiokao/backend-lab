from fastapi import Depends, HTTPException, status
from sqlalchemy import update
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.core.request_size import SizeLimitedAPIRouter
from app.database import get_db
from app.models import Category, Product, User

router = SizeLimitedAPIRouter(prefix="/categories")


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(
    category_id: int, db: Session = Depends(get_db), _: User = Depends(require_admin)
):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    db.execute(
        update(Product)
        .where(Product.category_id == category_id)
        .values(category_id=None)
    )
    db.delete(category)
    db.commit()
