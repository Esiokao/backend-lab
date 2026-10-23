import logging
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.dependencies import get_current_user, require_admin
from app.core.enums import OrderStatus
from app.core.events import ORDER_CREATED, ORDER_PAID
from app.database import get_db
from app.models import NotificationOutbox, Order, OrderItem, Product, User
from app.schemas.Order import OrderCreate, OrderResponse, PaymentResponse

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
    # 同一商品在請求中重複出現 → 拒絕（前端合併後再送）。
    product_ids = [item.product_id for item in payload.items]

    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(
            status_code=400,
            detail="Duplicate product in order",
        )

    # 一次撈全部商品：驗證存在 + 上架中 + 取得快照價格。
    products = (
        session.execute(select(Product).where(Product.id.in_(product_ids)))
        .scalars()
        .all()
    )

    products_by_id = {product.id: product for product in products}

    if len(products_by_id) != len(product_ids):
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    for product in products:
        if not product.is_active:
            raise HTTPException(
                status_code=404,
                detail="Product not found",
            )

    # 按 product_id 排序扣庫存：所有交易用同一順序拿鎖，死鎖免疫。
    quantities = {item.product_id: item.quantity for item in payload.items}

    for product_id in sorted(products_by_id):
        quantity = quantities[product_id]

        # 只有庫存足夠時才扣庫存，避免庫存被扣成負數。
        stock_update = session.execute(
            update(Product)
            .where(
                Product.id == product_id,
                Product.stock >= quantity,
            )
            .values(stock=Product.stock - quantity)
        )

        if stock_update.rowcount != 1:
            # 任一商品庫存不足 → rollback → 全部不扣。
            session.rollback()
            raise HTTPException(
                status_code=409,
                detail=f"Insufficient product stock: {product_id}",
            )

    # 訂單 owner 由目前登入的使用者決定。
    new_order = Order(
        user_id=current_user.id,
        status=OrderStatus.created.value,
    )
    session.add(new_order)

    # 先取得資料庫產生的訂單 ID，但尚未 commit。
    session.flush()

    # 明細（unit_price 快照）+ Outbox 事件：與訂單同一交易。
    for product_id in sorted(products_by_id):
        session.add(
            OrderItem(
                order_id=new_order.id,
                product_id=product_id,
                quantity=quantities[product_id],
                unit_price=products_by_id[product_id].price,
            )
        )

    outbox_event = NotificationOutbox(
        event_type=ORDER_CREATED,
        payload={"order_id": new_order.id},
    )
    session.add(outbox_event)

    # 任一寫入失敗，整個交易都不應只留下其中一筆。
    session.commit()
    session.refresh(new_order)

    return new_order


# a happy path payment.
@router.post("/orders/{order_id}/pay", response_model=PaymentResponse)
def pay_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    # 只允許付款自己的訂單。
    stmt = select(Order).where(
        Order.id == order_id,
        Order.user_id == current_user.id,
    )
    result = session.execute(stmt)
    order = result.scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.created.value:
        raise HTTPException(
            status_code=400,
            detail=f"Order cannot be paid in its current status: {order.status}",
        )

    # 建立付款成功的 Outbox 事件，交給 Worker 發送通知。Session commit 後才會有 order.id，避免事件 payload 內的 order_id 為 None。
    event = NotificationOutbox(
        event_type=ORDER_PAID,
        payload={"order_id": order.id},
    )

    # 模擬付款成功，更新訂單狀態與付款時間。
    order.status = OrderStatus.pending.value
    order.paid_at = func.now()
    session.add(event)
    session.commit()
    session.refresh(order)

    return {"message": "Payment successful", "order": order}


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
    stmt = select(Order).options(selectinload(Order.items))

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
    stmt = (
        select(Order)
        .options(selectinload(Order.items))
        .where(
            Order.id == order_id,
            Order.user_id == current_user.id,
        )
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
