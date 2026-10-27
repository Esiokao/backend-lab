"""處理站內通知相關的背景任務。"""

import logging
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any, TypeVar

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.core.enums import NotificationType
from app.core.events import EventType, user_channel
from app.core.redis import redis_client
from app.database import SessionLocal
from app.models import Notification, NotificationOutbox, Order, Product, ProductFollow
from app.schemas.WorkersJobPayload import (
    AdminNotificationJobPayload,
    OrderCancelledJobPayload,
    OrderCompletedJobPayload,
    OrderCreatedJobPayload,
    OrderPaidJobPayload,
    OutboxJobPayload,
    ProductRestockJobPayload,
)

logger = logging.getLogger(__name__)


# ── 共用骨架：載入 / 檢查 / 標記 outbox 事件 ─────────────────────────
JobT = TypeVar("JobT", bound=OutboxJobPayload)


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
    message: str,
) -> int:
    """以資料庫中的事件內容為準，不完全信任 RQ 傳入的 payload。"""
    value = event.payload.get(key)

    if type(value) is not int:
        raise ValueError(message)

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


def _create_order_notification(
    session: Session,
    event: NotificationOutbox,
    *,
    notification_type: NotificationType,
    title: str,
    body: str,
) -> None:
    """從事件取得訂單並建立單筆通知；body 用 {order_id} 當佔位符。"""
    order_id = _event_payload_int(
        event,
        "order_id",
        f"Outbox event {event.id} has an invalid order_id",
    )
    order = _get_or_raise(session, Order, order_id, f"Order not found: {order_id}")

    _create_notification_once(
        session,
        event,
        user_id=order.user_id,
        type=notification_type.value,
        title=title,
        body=body.format(order_id=order.id),
        data={"order_id": order.id},
    )
    return order.user_id


def _publish_refresh(user_ids: list[int]) -> None:
    """通知落庫後對各使用者頻道喊「該刷新了」。

    at-most-once：Redis 掛掉／當下沒人訂閱都不補發，漏掉的部分
    由前端輪詢兜底。所以這裡任何失敗只記 log，絕不讓 job 失敗——
    通知本身已經 commit 完成了。
    """
    for user_id in set(user_ids):
        try:
            redis_client.publish(user_channel(user_id), "refresh")
        except Exception:
            logger.warning(
                "SSE publish failed for user %s (poller will catch up)",
                user_id,
                exc_info=True,
            )


def _run_notification_job(
    payload: Any,
    payload_cls: type[JobT],
    *,
    session_factory: Callable[[], Session],
    expected_event_type: EventType | None,
    create_notifications: Callable[[Session, NotificationOutbox, JobT], list[int]],
):
    """所有通知任務共用的外殼：驗證 → 開交易 → 鎖事件 → 冪等檢查 → 建通知 → 標記完成 → 推播提醒。"""

    job = payload_cls.model_validate(payload)

    with session_factory() as session, session.begin():
        event = _load_outbox_event(session, job.outbox_event_id, expected_event_type)

        if _is_already_processed(event):
            logger.info("Outbox event already processed: id=%s", event.id)
            return

        # create_notifications 回傳「這次通知到了哪些使用者」，
        # commit 成功後才拿去喊話——沒 commit 就喊是開空頭支票。
        notified_user_ids = create_notifications(session, event, job)

        _mark_event_processed(event)

    _publish_refresh(notified_user_ids)

    logger.info("Notification job processed: outbox_event_id=%s", job.outbox_event_id)


# ── notification job ─────────────────────────


def notify_admin_notification(
    payload: AdminNotificationJobPayload,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """將 admin 定向通知事件轉成站內通知。"""

    def create_notifications(
        session: Session, event: NotificationOutbox, job: AdminNotificationJobPayload
    ) -> None:
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
        return [job.user_id]

    _run_notification_job(
        payload,
        AdminNotificationJobPayload,
        expected_event_type=EventType.admin_notification_created,
        session_factory=session_factory,
        create_notifications=create_notifications,
    )


def notify_product_restocked(
    payload: ProductRestockJobPayload,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """將商品補貨事件 fan-out 成每位關注者的到貨通知。"""

    def create_notifications(
        session: Session, event: NotificationOutbox, job: ProductRestockJobPayload
    ) -> None:
        product_id = _event_payload_int(
            event, "product_id", "outbox payload must contain an integer product_id"
        )
        product = _get_or_raise(
            session, Product, product_id, f"Product not found: {product_id}"
        )

        follower_ids = session.scalars(
            select(ProductFollow.user_id).where(ProductFollow.product_id == product_id)
        ).all()

        rows = [
            {
                "user_id": user_id,
                "type": NotificationType.product_restocked.value,
                "title": "商品補貨了",
                "body": f"您關注的商品 {product.name} 已補貨，快去看看吧！",
                "data": {"product_id": product_id},
                "source_event_id": event.id,
            }
            for user_id in follower_ids
        ]

        stmt = pg_insert(Notification).values(rows)

        stmt = stmt.on_conflict_do_nothing(
            index_elements=[
                "source_event_id",
                "user_id",
            ]  # ← 對應你的 unique constraint
        )
        session.execute(stmt)
        return follower_ids

    _run_notification_job(
        payload,
        ProductRestockJobPayload,
        expected_event_type=EventType.product_restocked,
        session_factory=session_factory,
        create_notifications=create_notifications,
    )


# ── order job ─────────────────────────


def notify_order_created(
    payload: OrderCreatedJobPayload,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """將訂單建立事件轉成站內通知，並確保重複執行不會重複建檔。"""

    def create_notifications(
        session: Session, event: NotificationOutbox, job: OrderCreatedJobPayload
    ) -> None:
        order_user_id = _create_order_notification(
            session,
            event,
            notification_type=NotificationType.order_created,
            title="訂單已建立",
            body="訂單編號 #{order_id} 已成功建立。",
        )
        return [order_user_id]

    _run_notification_job(
        payload,
        OrderCreatedJobPayload,
        expected_event_type=EventType.order_created,
        session_factory=session_factory,
        create_notifications=create_notifications,
    )


def notify_order_paid(
    payload: OrderPaidJobPayload,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """將訂單付款事件轉成站內通知，並確保重複執行不會重複建檔。"""

    def create_notifications(
        session: Session, event: NotificationOutbox, job: OrderPaidJobPayload
    ) -> None:
        order_user_id = _create_order_notification(
            session,
            event,
            notification_type=NotificationType.order_paid,
            title="訂單已付款",
            body="訂單 #{order_id} 已成功付款。點擊查看訂單詳情。",
        )
        return [order_user_id]

    _run_notification_job(
        payload,
        OrderPaidJobPayload,
        expected_event_type=EventType.order_paid,
        session_factory=session_factory,
        create_notifications=create_notifications,
    )


def notify_order_completed(
    payload: OrderCompletedJobPayload,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """將訂單完成事件轉成站內通知，並確保重複執行不會重複建檔。"""

    def create_notifications(
        session: Session, event: NotificationOutbox, job: OrderCompletedJobPayload
    ) -> None:
        order_user_id = _create_order_notification(
            session,
            event,
            notification_type=NotificationType.order_completed,
            title="訂單已完成",
            body="您的訂單 #{order_id} 已完成。感謝您的購買！",
        )
        return [order_user_id]

    _run_notification_job(
        payload,
        OrderCompletedJobPayload,
        expected_event_type=EventType.order_completed,
        session_factory=session_factory,
        create_notifications=create_notifications,
    )


def notify_order_cancelled(
    payload: OrderCancelledJobPayload,
    *,
    session_factory: Callable[[], Session] = SessionLocal,
) -> None:
    """將訂單取消事件轉成站內通知，並確保重複執行不會重複建檔。"""

    def create_notifications(
        session: Session, event: NotificationOutbox, job: OrderCancelledJobPayload
    ) -> None:
        order_user_id = _create_order_notification(
            session,
            event,
            notification_type=NotificationType.order_cancelled,
            title="訂單已取消",
            body="您的訂單 #{order_id} 已取消。如有疑問請聯絡客服",
        )
        return [order_user_id]

    _run_notification_job(
        payload,
        OrderCancelledJobPayload,
        expected_event_type=EventType.order_cancelled,
        session_factory=session_factory,
        create_notifications=create_notifications,
    )
