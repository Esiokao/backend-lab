"""處理站內通知相關的背景任務。"""

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import NotificationType
from app.core.events import EventType
from app.database import SessionLocal
from app.models import Notification, NotificationOutbox, Order, Product, ProductFollow
from app.schemas.Notification import AdminNotificationJobPayload
from app.schemas.Product import ProductRestockJobPayload

logger = logging.getLogger(__name__)


# ── 共用骨架：載入 / 檢查 / 標記 outbox 事件 ─────────────────────────


def _require_outbox_event_id(payload: dict[str, object]) -> int:
    """從 RQ payload 取得 outbox 事件 ID。"""
    outbox_event_id = payload.get("outbox_event_id")

    if type(outbox_event_id) is not int:
        raise TypeError("payload must contain an integer outbox_event_id")

    return outbox_event_id


def _load_outbox_event(
    session: Session,
    outbox_event_id: int,
    expected_type: EventType | None = None,
) -> NotificationOutbox:
    """鎖定並載入 outbox 事件，避免多個 Worker 同時處理同一筆。"""
    event = session.execute(
        select(NotificationOutbox)
        .where(NotificationOutbox.id == outbox_event_id)
        .with_for_update()
    ).scalar_one_or_none()

    if event is None:
        raise LookupError(f"Outbox event not found: {outbox_event_id}")

    if expected_type is not None and event.event_type != expected_type:
        raise ValueError(f"Unsupported outbox event type: {event.event_type}")

    return event


def _is_already_processed(event: NotificationOutbox) -> bool:
    """已完成的事件不再重複建立通知。"""
    return event.status == "processed" or event.processed_at is not None


def _mark_event_processed(event: NotificationOutbox) -> None:
    """事件與通知在同一個 transaction 中提交。"""
    event.status = "processed"
    event.processed_at = datetime.now(timezone.utc)
    event.last_error = None


def _event_payload_int(
    event: NotificationOutbox,
    key: str,
    exc_cls: type[Exception],
    message: str,
) -> int:
    """以資料庫中的事件內容為準，不完全信任 RQ 傳入的 payload。"""
    value = event.payload.get(key)

    if type(value) is not int:
        raise exc_cls(message)

    return value


def _get_or_raise(
    session: Session,
    model: type[Any],
    entity_id: int,
    message: str,
) -> Any:
    """依主鍵載入實體，不存在時丟出 LookupError。"""
    entity = session.get(model, entity_id)

    if entity is None:
        raise LookupError(message)

    return entity


def _create_notification_once(
    session: Session,
    event: NotificationOutbox,
    **fields: Any,
) -> None:
    """依 source_event_id 冪等建立單筆通知（重複執行不重複建檔）。"""
    existing = session.execute(
        select(Notification).where(Notification.source_event_id == event.id)
    ).scalar_one_or_none()

    if existing is None:
        session.add(Notification(source_event_id=event.id, **fields))


# ── 任務處理器 ──────────────────────────────────────────────────────


def notify_order_created(
    payload: dict[str, object],
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """將訂單建立事件轉成站內通知，並確保重複執行不會重複建檔。"""
    outbox_event_id = _require_outbox_event_id(payload)

    with session_factory() as session, session.begin():
        event = _load_outbox_event(session, outbox_event_id, EventType.order_created)

        if _is_already_processed(event):
            logger.info("Outbox event already processed: id=%s", event.id)
            return

        order_id = _event_payload_int(
            event,
            "order_id",
            ValueError,
            f"Outbox event {event.id} has an invalid order_id",
        )
        order = _get_or_raise(session, Order, order_id, f"Order not found: {order_id}")

        _create_notification_once(
            session,
            event,
            user_id=order.user_id,
            type=NotificationType.order_created.value,
            title="訂單已建立",
            body=f"訂單 #{order.id} 已成功建立。",
            data={"order_id": order.id},
        )

        _mark_event_processed(event)

    logger.info(
        "Order notification processed: outbox_event_id=%s",
        outbox_event_id,
    )


def notify_admin_notification(
    payload: AdminNotificationJobPayload,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """將 admin 定向通知事件轉成站內通知。"""
    job = AdminNotificationJobPayload.model_validate(payload)

    with session_factory() as session, session.begin():
        event = _load_outbox_event(session, job.outbox_event_id)

        if _is_already_processed(event):
            logger.info("Outbox event already processed: id=%s", event.id)
            return

        session.add(
            Notification(
                user_id=job.user_id,
                type=job.type,
                title=job.title,
                body=job.body,
                data={},
                source_event_id=event.id,
            )
        )

        _mark_event_processed(event)


def notify_product_restocked(
    payload: ProductRestockJobPayload,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """將商品補貨事件 fan-out 成每位關注者的到貨通知。"""
    job = ProductRestockJobPayload.model_validate(payload)

    with session_factory() as session, session.begin():
        event = _load_outbox_event(session, job.outbox_event_id)

        if _is_already_processed(event):
            logger.info("Outbox event already processed: id=%s", event.id)
            return

        product_id = _event_payload_int(
            event,
            "product_id",
            TypeError,
            "outbox payload must contain an integer product_id",
        )
        product = _get_or_raise(
            session, Product, product_id, f"Product not found: {product_id}"
        )

        follower_ids = session.scalars(
            select(ProductFollow.user_id).where(
                ProductFollow.product_id == product_id,
            )
        ).all()

        for user_id in follower_ids:
            session.add(
                Notification(
                    user_id=user_id,
                    type=NotificationType.product_restocked.value,
                    title="商品補貨了",
                    body=f"{product.name} 已補貨",
                    data={"product_id": product_id},
                    source_event_id=event.id,
                )
            )

        _mark_event_processed(event)


def notify_order_paid(
    payload: dict[str, object],
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """將訂單付款事件轉成站內通知，並確保重複執行不會重複建檔。"""
    outbox_event_id = _require_outbox_event_id(payload)

    with session_factory() as session, session.begin():
        event = _load_outbox_event(session, outbox_event_id, EventType.order_paid)

        if _is_already_processed(event):
            logger.info("Outbox event already processed: id=%s", event.id)
            return

        order_id = _event_payload_int(
            event,
            "order_id",
            ValueError,
            f"Outbox event {event.id} has an invalid order_id",
        )
        order = _get_or_raise(session, Order, order_id, f"Order not found: {order_id}")

        _create_notification_once(
            session,
            event,
            user_id=order.user_id,
            type=NotificationType.order_paid.value,
            title="訂單已付款",
            body=f"訂單 #{order.id} 已成功付款。",
            data={"order_id": order.id},
        )

        _mark_event_processed(event)

    logger.info(
        "Order notification processed: outbox_event_id=%s",
        outbox_event_id,
    )
