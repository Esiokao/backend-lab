from fastapi import HTTPException, status
from sqlalchemy import update

from app.core.dependencies import AdminUser
from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Category, Product

router = SizeLimitedAPIRouter(prefix="/categories")


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_category(category_id: int, db: DbSession, _: AdminUser):
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
