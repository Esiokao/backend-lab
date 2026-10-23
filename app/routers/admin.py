from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.core.enums import ALLOWED_TRANSITIONS, OrderStatus
from app.database import get_db
from app.models import Order, User
from app.schemas.User import AdminUserPatch, UserResponse

router = APIRouter(
    prefix="/admin/orders",
    tags=["Admin Orders"],
)


@router.get("")
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


# ── Admin 使用者管理 ────────────────────────────────────────────────

users_router = APIRouter(
    prefix="/admin/users",
    tags=["Admin Users"],
)


@users_router.patch("/{user_id}", response_model=UserResponse)
def update_user_as_admin(
    user_id: int,
    payload: AdminUserPatch,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    """admin 更新使用者資料（name/email/role）。"""
    # 防呆：admin 不能改變自己的 role，避免把自己鎖在門外。
    if payload.role is not None and current_admin.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    user = db.get(User, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    update_data = payload.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        setattr(user, field, value)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already exists",
        )

    db.refresh(user)
    return user
