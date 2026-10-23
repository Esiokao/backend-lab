from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.core.events import EventType
from app.database import get_db
from app.models import NotificationOutbox, Product, User
from app.schemas.Product import ProductPatch, ProductResponse

router = APIRouter(prefix="/products")


@router.patch(
    "/{product_id}",
    response_model=ProductResponse,
)
def update_product(
    product_id: int,
    payload: ProductPatch,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    old_stock = product.stock
    update_data = payload.model_dump(
        exclude_unset=True,
        exclude_none=True,
    )

    for field, value in update_data.items():
        setattr(product, field, value)

    new_stock = product.stock

    # 只在庫存從無貨變成有貨時建立補貨事件。
    # 其他庫存變動不通知，避免每次扣庫存都通知追蹤者。
    if old_stock == 0 and new_stock > 0:
        db.add(
            NotificationOutbox(
                event_type=EventType.product_restocked,
                payload={"product_id": product.id},
            )
        )

    db.commit()
    db.refresh(product)

    return product
