from sqlalchemy import select

from app.core.dependencies import AdminUser
from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Product
from app.schemas.Product import ProductResponse

router = SizeLimitedAPIRouter(prefix="/products")


@router.get("/archived", response_model=list[ProductResponse])
def list_archived_products(
    db: DbSession,
    _: AdminUser,
):
    # 只查詢已下架的商品，供 Admin 管理。
    stmt = (
        select(Product).where(Product.is_active.is_(False)).order_by(Product.id.desc())
    )

    return db.scalars(stmt).all()
