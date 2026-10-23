from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database import get_db
from app.models import Product, User
from app.schemas.Product import ProductResponse

router = APIRouter(prefix="/products")


@router.patch(
    "/{product_id}/archive",
    response_model=ProductResponse,
)
def archive_product(
    product_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    # 將商品設為下架，但保留資料供訂單與 Admin 查詢。
    product.is_active = False
    db.commit()
    db.refresh(product)

    return product
