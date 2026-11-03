from fastapi import HTTPException
from sqlalchemy import select

from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Product
from app.schemas.Product import ProductResponse

router = SizeLimitedAPIRouter(prefix="/products")


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: DbSession,
):
    product = db.scalar(
        select(Product).where(
            Product.id == product_id,
            Product.is_active.is_(True),
        )
    )

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return product
