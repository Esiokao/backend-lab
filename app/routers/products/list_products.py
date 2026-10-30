from typing import Literal

from fastapi import Query
from sqlalchemy import desc, select

from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Product
from app.schemas.Product import ProductResponse

# 排序選項：缺省維持 id 遞增（向後相容——無限滾動預取與既有測試都依賴這個順序）。
SortKey = Literal["newest", "price_asc", "price_desc"]

router = SizeLimitedAPIRouter(prefix="/products")


@router.get("", response_model=list[ProductResponse])
def list_products(
    db: DbSession,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    q: str | None = Query(default=None),
    category_id: int | None = Query(default=None, gt=0),
    sort: SortKey | None = Query(default=None),
):
    # 前台只顯示上架商品。
    stmt = select(Product).where(
        Product.is_active.is_(True),
    )

    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q}%"))

    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)

    # 每個排序鍵都補 id 當 tie-breaker：offset 分頁需要全序才不會
    # 在同價/同時間的商品之間重複或漏掉（第 1、2 頁各看到同一筆）。
    match sort:
        case "newest":
            stmt = stmt.order_by(desc(Product.created_at), desc(Product.id))
        case "price_asc":
            stmt = stmt.order_by(Product.price, Product.id)
        case "price_desc":
            stmt = stmt.order_by(desc(Product.price), desc(Product.id))
        case _:
            stmt = stmt.order_by(Product.id)

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)

    return db.scalars(stmt).all()
