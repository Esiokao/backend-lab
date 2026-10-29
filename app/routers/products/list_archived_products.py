from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.core.request_size import SizeLimitedAPIRouter
from app.database import get_db
from app.models import Product, User
from app.schemas.Product import ProductResponse

router = SizeLimitedAPIRouter(prefix="/products")


@router.get("/archived", response_model=list[ProductResponse])
def list_archived_products(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    # 只查詢已下架的商品，供 Admin 管理。
    stmt = (
        select(Product).where(Product.is_active.is_(False)).order_by(Product.id.desc())
    )

    return db.scalars(stmt).all()
