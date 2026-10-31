"""過期未付款訂單的自動取消 worker。

created 超過 ORDER_EXPIRY_SECONDS 仍未付款 → cancelled + 歸還庫存 + 發取消通知。
堵住「未付款訂單鎖死庫存」的攻擊面：登入者建單不付款即可囤積庫存，
沒有過期機制時，這個攻擊零成本且永不釋放（真實電商的「15 分鐘未付款自動取消」同款）。
"""

import logging
import os
import time
from datetime import timedelta

from sqlalchemy import func, select, update

from app.core.enums import OrderStatus
from app.core.events import EventType
from app.database import SessionLocal
from app.models import NotificationOutbox, Order, OrderItem, Product

logger = logging.getLogger(__name__)

# 未付款訂單的存活時間；超過即自動取消並歸還庫存。
ORDER_EXPIRY_SECONDS = int(os.getenv("ORDER_EXPIRY_SECONDS", "1800"))
POLL_INTERVAL_SECONDS = 5
BATCH_SIZE = 100


def _claim_batch(session) -> list[Order]:
    """撈出過期的未付款訂單（skip_locked，多實體安全）。

    時鐘比較留在 SQL 內（created_at vs 資料庫的 now()）——
    不吃 worker 本機的鐘，避免容器時鐘偏差（31b8b76 的教訓）。
    """
    stmt = (
        select(Order)
        .where(
            Order.status == OrderStatus.created.value,
            Order.created_at <= func.now() - timedelta(seconds=ORDER_EXPIRY_SECONDS),
        )
        .order_by(Order.id)
        .limit(BATCH_SIZE)
        .with_for_update(skip_locked=True)
    )
    return list(session.execute(stmt).scalars().all())


def expire_once(session) -> int:
    """取消一批過期的未付款訂單（含歸還庫存），回傳本輪處理的筆數。"""
    orders = _claim_batch(session)
    expired = 0

    for order in orders:
        # 歸還庫存：與 create_order 的扣庫存、cancel 的歸還對稱（同排序，死鎖免疫）。
        items = (
            session.execute(select(OrderItem).where(OrderItem.order_id == order.id))
            .scalars()
            .all()
        )
        quantities = {item.product_id: item.quantity for item in items}
        for product_id in sorted(quantities):
            session.execute(
                update(Product)
                .where(Product.id == product_id)
                .values(stock=Product.stock + quantities[product_id])
            )

        order.status = OrderStatus.cancelled.value
        session.add(
            NotificationOutbox(
                event_type=EventType.order_cancelled,
                payload={"order_id": order.id},
            )
        )
        expired += 1

    if expired:
        session.commit()
    return expired


def run_order_expiry_worker() -> None:
    """持續輪詢過期訂單；短暫失敗不會終止整個 Worker。"""
    while True:
        try:
            with SessionLocal() as session:
                expired = expire_once(session)
                if expired:
                    logger.info("Order expiry cancelled %s orders", expired)
        except Exception:
            logger.exception("Order expiry worker iteration failed")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_order_expiry_worker()
