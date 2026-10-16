import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.dependencies import get_current_user, require_admin
from app.core.queue import get_task_publisher
from app.core.task_publisher import TaskPublisher
from app.database import get_db
from app.models import Order, User

router = APIRouter(
    tags=["Orders"],
)
logger = logging.getLogger(__name__)


@router.post("/orders")
def create_order(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    publisher: TaskPublisher = Depends(get_task_publisher),
):
    # 訂單 owner 由目前登入的使用者決定。
    new_order = Order(user_id=current_user.id)
    session.add(new_order)
    session.commit()
    session.refresh(new_order)

    # 訂單提交成功後，才發布背景通知任務。
    try:
        publisher.enqueue(
            "notifications.order_created",
            {"order_id": new_order.id},
        )
    except Exception:
        # 通知發布失敗時記錄錯誤，不讓通知故障影響訂單 API。
        logger.exception(
            "Failed to enqueue order-created notification: order_id=%s",
            new_order.id,
        )

    return new_order


@router.get("/orders")
def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user_id: int | None = Query(None),
    sort_by: Literal["id", "user_id"] = "id",
    order: Literal["asc", "desc"] = "asc",
    session: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Order)

    # 一般使用者只能看自己的訂單；admin 可看全部，或用 user_id 過濾特定使用者。
    if current_user.role != "admin":
        stmt = stmt.where(Order.user_id == current_user.id)
    elif user_id is not None:
        stmt = stmt.where(Order.user_id == user_id)

    stmt = stmt.order_by(getattr(getattr(Order, sort_by), order)())
    stmt = stmt.offset((page - 1) * page_size)
    stmt = stmt.limit(page_size)

    result = session.execute(stmt)
    return result.scalars().all()


@router.get("/orders/{order_id}")
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    # 只允許取得目前登入者自己的訂單。
    stmt = select(Order).where(
        Order.id == order_id,
        Order.user_id == current_user.id,
    )
    result = session.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    return order


@router.get("/users/{user_id}/orders")
def get_user_orders(
    user_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    # 只能查詢自己的訂單。
    if user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access another user's orders",
        )

    stmt = select(Order).where(Order.user_id == current_user.id)
    result = session.execute(stmt)
    return result.scalars().all()


@router.get("/users-with-orders")
def get_users_with_orders(
    current_user: User = Depends(require_admin),
    session: Session = Depends(get_db),
):
    # 只有 admin 可以查看所有使用者的訂單。
    users = (
        session.execute(select(User).options(selectinload(User.orders))).scalars().all()
    )

    return {
        "users": [
            {"name": user.name, "order_count": len(user.orders)} for user in users
        ]
    }
