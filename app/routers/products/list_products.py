from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Product
from app.schemas.Product import ProductResponse

router = APIRouter(prefix="/products")


@router.get("", response_model=list[ProductResponse])
def list_products(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    q: str | None = Query(default=None),
    catalog_id: int | None = Query(default=None, gt=0),
    db: Session = Depends(get_db),
):
    # 前台只顯示上架商品。
    stmt = select(Product).where(
        Product.is_active.is_(True),
    )

    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q}%"))

    if catalog_id is not None:
        stmt = stmt.where(Product.catalog_id == catalog_id)

    stmt = stmt.order_by(Product.id).offset((page - 1) * page_size).limit(page_size)

    return db.scalars(stmt).all()
