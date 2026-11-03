from fastapi import HTTPException

from app.core.dependencies import AdminUser
from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Product
from app.schemas.Product import ProductResponse

router = SizeLimitedAPIRouter(prefix="/products")


@router.patch(
    "/{product_id}/restore",
    response_model=ProductResponse,
)
def restore_product(
    product_id: int,
    db: DbSession,
    _: AdminUser,
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    # 將已封存商品重新設為上架狀態。
    product.is_active = True
    db.commit()
    db.refresh(product)

    return product
