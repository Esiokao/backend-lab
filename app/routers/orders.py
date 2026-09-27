from typing_extensions import Literal

from app.core.dependencies import get_current_user, require_admin
from app.database import get_db
from app.models import Order, User
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

router = APIRouter()


@router.post("/orders")
def create_order(
    current_user: User = Depends(get_current_user),  # noqa: B008
    session: Session = Depends(get_db),  # noqa: B008
):
    # Order 的 owner 由 JWT 對應的 User 決定
    new_order = Order(
        user_id=current_user.id,
    )

    session.add(new_order)
    session.commit()
    session.refresh(new_order)

    return new_order


@router.get("/orders")
def get_orders(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user_id: int | None = Query(None),
    sort_by: Literal["id", "user_id"] = "id",
    order: Literal["asc", "desc"] = "asc",
    session: Session = Depends(get_db),  # noqa: B008
):
    stmt = select(Order)
    # Pagination
    if user_id is not None:
        stmt = stmt.where(Order.user_id == user_id)

    # Sort the results based on sort_by and order parameters
    stmt = stmt.order_by(getattr(getattr(Order, sort_by), order)())
    # Offset and Limit for pagination
    stmt = stmt.offset((page - 1) * page_size)
    # Limit the number of results returned to page_size
    stmt = stmt.limit(page_size)
    result = session.execute(stmt)

    return result.scalars().all()


@router.get("/orders/{order_id}")
def get_order(
    order_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    session: Session = Depends(get_db),  # noqa: B008
):
    # 只允許取得目前登入者自己的 Order

    stmt = select(Order).where(
        Order.id == order_id,
        Order.user_id == current_user.id,
    )

    result = session.execute(stmt)

    order = result.scalar_one_or_none()

    # Order 不存在，或不屬於目前使用者
    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    return order


@router.get("/users/{user_id}/orders")
def get_user_orders(
    user_id: int,
    current_user: User = Depends(get_current_user),  # noqa: B008
    session: Session = Depends(get_db),  # noqa: B008
):
    # 只能查自己的 Orders
    if user_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You cannot access another user's orders",
        )

    stmt = select(Order).where(
        Order.user_id == current_user.id,
    )

    result = session.execute(stmt)

    return result.scalars().all()


@router.get("/users-with-orders")
def get_users_with_orders(
    current_user: User = Depends(require_admin),
    session: Session = Depends(get_db),
):
    # 只有 admin 可以查看所有使用者的 Orders
    users = (
        session.execute(select(User).options(selectinload(User.orders))).scalars().all()
    )

    return {
        "users": [
            {
                "name": user.name,
                "order_count": len(user.orders),
            }
            for user in users
        ]
    }
