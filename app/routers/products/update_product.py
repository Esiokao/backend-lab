from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.core.events import EventType
from app.database import get_db
from app.models import Catalog, NotificationOutbox, Product, User
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

    # 允許明確用 null 解除商品分類；其他 nullable 欄位維持既有行為。
    if "catalog_id" in payload.model_fields_set and payload.catalog_id is None:
        update_data["catalog_id"] = None

    if (
        update_data.get("catalog_id") is not None
        and db.get(Catalog, update_data["catalog_id"]) is None
    ):
        raise HTTPException(status_code=404, detail="Catalog not found")

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
