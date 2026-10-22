from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database import get_db
from app.models import Order, Product, User

router = APIRouter()


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_product(
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

    # 商品只要被既有訂單引用，就不能刪除。
    # 這裡先檢查，讓 API 穩定回傳 409，
    # 不依賴資料庫在 commit 時才拋出 IntegrityError。
    referenced_order_id = db.scalar(
        select(Order.id).where(Order.product_id == product_id).limit(1)
    )

    if referenced_order_id is not None:
        raise HTTPException(
            status_code=409,
            detail="Product is referenced by existing orders",
        )

    # 沒有訂單引用時才真正刪除商品。
    # ProductFollow 的 ON DELETE CASCADE 會一併刪除關注資料。
    db.delete(product)
    db.commit()
