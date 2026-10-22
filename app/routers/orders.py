import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update
from sqlalchemy.orm import Session, selectinload

from app.core.dependencies import get_current_user, require_admin
from app.core.events import ORDER_CREATED
from app.database import get_db
from app.models import NotificationOutbox, Order, Product, User
from app.schemas.Order import OrderCreate, OrderResponse

router = APIRouter(
    tags=["Orders"],
)
logger = logging.getLogger(__name__)


@router.post(
    "/orders",
    response_model=OrderResponse,
)
def create_order(
    payload: OrderCreate,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    product = session.get(Product, payload.product_id)

    if product is None or not product.is_active:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    # 只有庫存足夠時才扣庫存，避免庫存被扣成負數。
    stock_update = session.execute(
        update(Product)
        .where(
            Product.id == payload.product_id,
            Product.stock >= payload.quantity,
        )
        .values(stock=Product.stock - payload.quantity)
    )

    if stock_update.rowcount != 1:
        raise HTTPException(
            status_code=409,
            detail="Insufficient product stock",
        )
    # 訂單 owner 由目前登入的使用者決定。
    new_order = Order(
        user_id=current_user.id,
        product_id=payload.product_id,
        quantity=payload.quantity,
    )
    session.add(new_order)

    # 先取得資料庫產生的訂單 ID，但尚未 commit。
    session.flush()

    # 訂單與 Outbox 事件在同一個交易中提交。
    outbox_event = NotificationOutbox(
        event_type=ORDER_CREATED,
        payload={"order_id": new_order.id},
    )
    session.add(outbox_event)

    # 任一寫入失敗，整個交易都不應只留下其中一筆。
    session.commit()
    session.refresh(new_order)

    return new_order


@router.get("/orders", response_model=list[OrderResponse])
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


@router.get(
    "/orders/{order_id}",
    response_model=OrderResponse,
)
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


@router.get(
    "/users/{user_id}/orders",
    response_model=list[OrderResponse],
)
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
