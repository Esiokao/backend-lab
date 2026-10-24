from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.redis import redis_client
from app.core.visitors import visitors_today_count, visitors_total_count
from app.database import get_db
from app.models import Notification, Order, OrderItem, User

router = APIRouter(prefix="/stats", tags=["Stats"])


@router.get("")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """儀表板真實數據，依角色分範圍：

    - admin：全站 total_users / total_orders / orders_today / total_revenue / revenue_today / visitors_today
    - 一般使用者：自己的 total_orders / orders_today / unread_notifications

    營收 = order_items 的 unit_price 快照 × quantity（排除 cancelled 訂單）；
    訪客 = middleware 以匿名 cookie 記入 Redis 的每日唯一集合。

    （直接 COUNT 查詢；demo 資料量小，先不引入 Redis 快取，量大再補 60s cache）
    """
    today = datetime.now(timezone.utc).date()

    if current_user.role == "admin":
        total_users = db.scalar(select(func.count()).select_from(User))
        total_orders = db.scalar(select(func.count()).select_from(Order))
        orders_today = db.scalar(
            select(func.count())
            .select_from(Order)
            .where(func.date(Order.created_at) == today)
        )

        # 營收：unit_price 快照 × quantity；取消的訂單不算收入。
        revenue_stmt = (
            select(
                func.coalesce(func.sum(OrderItem.unit_price * OrderItem.quantity), 0)
            )
            .join(Order, Order.id == OrderItem.order_id)
            .where(
                Order.status != "cancelled",
            )
        )
        total_revenue = db.scalar(revenue_stmt)
        revenue_today = db.scalar(
            revenue_stmt.where(func.date(Order.created_at) == today)
        )

        return {
            "scope": "global",
            "total_users": total_users,
            "total_orders": total_orders,
            "orders_today": orders_today,
            "total_revenue": float(total_revenue),
            "revenue_today": float(revenue_today),
            "visitors_today": visitors_today_count(redis_client),
            "visitors_total": visitors_total_count(redis_client),
        }

    total_orders = db.scalar(
        select(func.count()).select_from(Order).where(Order.user_id == current_user.id)
    )
    orders_today = db.scalar(
        select(func.count())
        .select_from(Order)
        .where(Order.user_id == current_user.id, func.date(Order.created_at) == today)
    )
    unread_notifications = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None),
        )
    )
    return {
        "scope": "personal",
        "total_orders": total_orders,
        "orders_today": orders_today,
        "unread_notifications": unread_notifications,
    }
