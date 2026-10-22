"""處理站內通知相關的背景任務。"""

import logging
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import ORDER_CREATED
from app.database import SessionLocal
from app.models import Notification, NotificationOutbox, Order, Product, ProductFollow
from app.schemas.Notification import AdminNotificationJobPayload
from app.schemas.Product import ProductRestockJobPayload

logger = logging.getLogger(__name__)


def notify_order_created(
    payload: dict[str, object],
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """將訂單建立事件轉成站內通知，並確保重複執行不會重複建檔。"""
    outbox_event_id = payload.get("outbox_event_id")

    if type(outbox_event_id) is not int:
        raise TypeError("payload must contain an integer outbox_event_id")

    with session_factory() as session, session.begin():
        # 鎖定事件，避免多個 Worker 同時處理同一筆事件。
        event = session.execute(
            select(NotificationOutbox)
            .where(NotificationOutbox.id == outbox_event_id)
            .with_for_update()
        ).scalar_one_or_none()

        if event is None:
            raise LookupError(f"Outbox event not found: {outbox_event_id}")

        if event.event_type != ORDER_CREATED:
            raise ValueError(f"Unsupported outbox event type: {event.event_type}")

        # 已完成的事件不再重複建立通知。
        if event.status == "processed" or event.processed_at is not None:
            logger.info(
                "Outbox event already processed: id=%s",
                event.id,
            )
            return

        # 以資料庫中的事件內容為準，不完全信任 RQ 傳入的 payload。
        order_id = event.payload.get("order_id")

        if type(order_id) is not int:
            raise ValueError(f"Outbox event {event.id} has an invalid order_id")

        order = session.get(Order, order_id)

        if order is None:
            raise LookupError(f"Order not found: {order_id}")

        # 先檢查唯一來源事件，提供額外的冪等性保護。
        notification = session.execute(
            select(Notification).where(Notification.source_event_id == event.id)
        ).scalar_one_or_none()

        if notification is None:
            notification = Notification(
                user_id=order.user_id,
                type="order_created",
                title="訂單已建立",
                body=f"訂單 #{order.id} 已成功建立。",
                data={"order_id": order.id},
                source_event_id=event.id,
            )
            session.add(notification)

        # 通知與事件狀態在同一個 transaction 中提交。
        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        event.last_error = None

    logger.info(
        "Order notification processed: outbox_event_id=%s",
        outbox_event_id,
    )


# ADMIN CAN CREATE NOTIFICATIONS
def notify_admin_notification(
    payload: AdminNotificationJobPayload,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    job = AdminNotificationJobPayload.model_validate(payload)

    with session_factory() as session, session.begin():
        event = session.execute(
            select(NotificationOutbox)
            .where(NotificationOutbox.id == job.outbox_event_id)
            .with_for_update()
        ).scalar_one_or_none()

        if event is None:
            raise LookupError(f"Outbox event not found: {job.outbox_event_id}")

        if event.status == "processed" or event.processed_at is not None:
            return

        notification = Notification(
            user_id=job.user_id,
            type=job.type,
            title=job.title,
            body=job.body,
            data={},
            source_event_id=event.id,
        )
        session.add(notification)

        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        event.last_error = None


def notify_product_restocked(
    payload: ProductRestockJobPayload,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    _payload = ProductRestockJobPayload.model_validate(payload)
    outbox_event_id = _payload.outbox_event_id

    with session_factory() as session, session.begin():
        event = session.execute(
            select(NotificationOutbox)
            .where(NotificationOutbox.id == outbox_event_id)
            .with_for_update()
        ).scalar_one_or_none()

        if event is None:
            raise LookupError(f"Outbox event not found: {outbox_event_id}")

        if event.status == "processed" or event.processed_at is not None:
            return

        product_id = event.payload.get("product_id")

        if type(product_id) is not int:
            raise TypeError("outbox payload must contain an integer product_id")

        product = session.get(Product, product_id)

        if product is None:
            raise LookupError(f"Product not found: {product_id}")

        follower_ids = session.scalars(
            select(ProductFollow.user_id).where(
                ProductFollow.product_id == product_id,
            )
        ).all()

        for user_id in follower_ids:
            session.add(
                Notification(
                    user_id=user_id,
                    type="product_restocked",
                    title="商品補貨了",
                    body=f"{product.name} 已補貨",
                    data={"product_id": product_id},
                    source_event_id=event.id,
                )
            )

        event.status = "processed"
        event.processed_at = datetime.now(timezone.utc)
        event.last_error = None
