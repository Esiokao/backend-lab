from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database import get_db
from app.models import Order, User

router = APIRouter(
    prefix="/admin/orders",
    tags=["Admin Orders"],
)

# 定義允許使用的訂單狀態。
OrderStatus = Literal["pending", "processing", "completed", "cancelled"]

# 定義合法的狀態轉換。
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "pending": {"processing", "cancelled"},
    "processing": {"completed", "cancelled"},
    "completed": set(),
    "cancelled": set(),
}


@router.get("/")
def list_orders(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100),
    order_status: OrderStatus | None = Query(default=None, alias="status"),
    user_id: int | None = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """列出訂單，支援分頁與狀態、使用者篩選。"""
    stmt = select(Order)

    if order_status is not None:
        stmt = stmt.where(Order.status == order_status)

    if user_id is not None:
        stmt = stmt.where(Order.user_id == user_id)

    # 固定排序，確保分頁結果穩定。
    stmt = stmt.order_by(Order.id)

    total_stmt = select(Order.id)

    if order_status is not None:
        total_stmt = total_stmt.where(Order.status == order_status)

    if user_id is not None:
        total_stmt = total_stmt.where(Order.user_id == user_id)

    total = len(db.scalars(total_stmt).all())

    stmt = stmt.offset((page - 1) * page_size).limit(page_size)
    orders = db.scalars(stmt).all()

    return {
        "items": [
            {
                "id": order.id,
                "user_id": order.user_id,
                "status": order.status,
            }
            for order in orders
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.patch("/{order_id}/status")
def update_order_status(
    order_id: int,
    new_status: OrderStatus,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """更新訂單狀態，並拒絕不合法的狀態轉換。"""
    order = db.get(Order, order_id)

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if new_status not in ALLOWED_TRANSITIONS.get(order.status, set()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot change order status from {order.status} to {new_status}",
        )

    order.status = new_status
    db.commit()
    db.refresh(order)

    return {
        "id": order.id,
        "user_id": order.user_id,
        "status": order.status,
    }


@router.delete("/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_order(
    order_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    """刪除指定訂單。"""
    order = db.get(Order, order_id)

    if order is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    db.delete(order)
    db.commit()
