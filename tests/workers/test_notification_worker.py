from decimal import Decimal

import pytest
from sqlalchemy import func, select

from app.core.events import ADMIN_NOTIFICATION_CREATED, PRODUCT_RESTOCKED
from app.models import Notification, Product, ProductFollow
from app.workers.notifications import (
    notify_admin_notification,
    notify_order_created,
    notify_product_restocked,
)


def test_worker_creates_notification(
    test_db,
    create_test_user,
    test_user_data,
    create_test_order,
    create_test_outbox_event,
    worker_session_factory,
):
    # Arrange：建立使用者、訂單與 Outbox 事件。
    user = create_test_user(**test_user_data)
    order = create_test_order(user_id=user.id)
    event = create_test_outbox_event(
        payload={"order_id": order.id},
    )

    # Act：執行 Worker。
    notify_order_created(
        {"outbox_event_id": event.id},
        session_factory=worker_session_factory,
    )

    # Assert：確認通知與事件狀態。
    notification = test_db.execute(
        select(Notification).where(Notification.source_event_id == event.id)
    ).scalar_one()

    test_db.refresh(event)

    assert notification.user_id == user.id
    assert notification.type == "order_created"
    assert notification.data == {"order_id": order.id}
    assert event.status == "processed"
    assert event.processed_at is not None


def test_worker_does_not_create_duplicate_notification(
    test_db,
    create_test_user,
    test_user_data,
    create_test_order,
    create_test_outbox_event,
    worker_session_factory,
):
    # Arrange：建立一個有效的訂單事件。
    user = create_test_user(**test_user_data)
    order = create_test_order(user_id=user.id)
    event = create_test_outbox_event(
        payload={"order_id": order.id},
    )

    payload = {"outbox_event_id": event.id}

    # Act：對同一個事件執行兩次。
    notify_order_created(payload, session_factory=worker_session_factory)
    notify_order_created(payload, session_factory=worker_session_factory)

    # Assert：同一事件只能有一筆通知。
    count = test_db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.source_event_id == event.id)
    )

    assert count == 1

    test_db.refresh(event)
    assert event.status == "processed"
    assert event.processed_at is not None


def test_worker_raises_error_when_outbox_event_not_found(
    worker_session_factory,
):
    # 使用不存在的 Outbox ID，確認 Worker 不會默默忽略錯誤。
    with pytest.raises(LookupError, match="Outbox event not found"):
        notify_order_created(
            {"outbox_event_id": 999999999},
            session_factory=worker_session_factory,
        )


def test_worker_rejects_unsupported_event_type(
    test_db,
    create_test_outbox_event,
    worker_session_factory,
):
    # 建立不支援的事件類型。
    event = create_test_outbox_event(
        event_type="notifications.unknown",
        payload={"order_id": 1},
    )

    # Worker 應該拒絕處理這種事件。
    with pytest.raises(ValueError, match="Unsupported outbox event type"):
        notify_order_created(
            {"outbox_event_id": event.id},
            session_factory=worker_session_factory,
        )

    # 確認失敗的事件沒有被標記為已處理。
    test_db.refresh(event)
    assert event.status == "pending"


def test_worker_rejects_non_integer_outbox_event_id(worker_session_factory):
    # payload 的 outbox_event_id 必須是整數。
    with pytest.raises(TypeError, match="outbox_event_id"):
        notify_order_created(
            {"outbox_event_id": "42"},
            session_factory=worker_session_factory,
        )


def test_worker_raises_error_when_order_not_found(
    test_db,
    create_test_outbox_event,
    worker_session_factory,
):
    # 建立事件，引用一筆不存在的訂單。
    event = create_test_outbox_event(
        payload={"order_id": 999999999},
    )

    with pytest.raises(LookupError, match="Order not found"):
        notify_order_created(
            {"outbox_event_id": event.id},
            session_factory=worker_session_factory,
        )

    # 重新讀取資料庫狀態，確認失敗事件沒有被標記為完成。
    test_db.refresh(event)
    assert event.status == "pending"
    assert event.processed_at is None
    assert event.last_error is None

    # 確認這次失敗沒有產生通知。
    notification_count = test_db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.source_event_id == event.id)
    )
    assert notification_count == 0


def test_admin_worker_creates_notification(
    test_db,
    create_test_user,
    test_user_data,
    create_test_outbox_event,
    worker_session_factory,
):
    user = create_test_user(**test_user_data)

    event = create_test_outbox_event(
        event_type=ADMIN_NOTIFICATION_CREATED,
        payload={
            "user_id": user.id,
            "type": "admin_announcement",
            "title": "系統公告",
            "body": "今晚維護。",
        },
    )

    notify_admin_notification(
        {
            "outbox_event_id": event.id,
            "user_id": user.id,
            "type": "admin_announcement",
            "title": "系統公告",
            "body": "今晚維護。",
        },
        session_factory=worker_session_factory,
    )

    notification = test_db.execute(
        select(Notification).where(Notification.source_event_id == event.id)
    ).scalar_one()

    assert notification.user_id == user.id
    assert notification.type == "admin_announcement"
    assert notification.title == "系統公告"
    assert notification.body == "今晚維護。"

    test_db.refresh(event)
    assert event.status == "processed"


def test_restock_worker_notifies_all_followers(
    test_db,
    create_test_user,
    test_user_data,
    create_test_order,
    create_test_outbox_event,
    worker_session_factory,
):
    user_a = create_test_user(**test_user_data)

    user_b_data = {
        **test_user_data,
        "email": "user-b@example.com",
        "name": "User B",
    }
    user_b = create_test_user(**user_b_data)

    product = Product(
        name="Coffee Beans",
        price=Decimal("19.99"),
        stock=10,
    )
    test_db.add(product)
    test_db.flush()

    test_db.add_all(
        [
            ProductFollow(
                user_id=user_a.id,
                product_id=product.id,
            ),
            ProductFollow(
                user_id=user_b.id,
                product_id=product.id,
            ),
        ]
    )

    event = create_test_outbox_event(
        event_type=PRODUCT_RESTOCKED,
        payload={"product_id": product.id},
    )

    notify_product_restocked(
        {
            "product_id": product.id,
            "outbox_event_id": event.id,
        },
        session_factory=worker_session_factory,
    )

    notifications = test_db.scalars(
        select(Notification).where(
            Notification.source_event_id == event.id,
        )
    ).all()

    assert len(notifications) == 2
    assert {notification.user_id for notification in notifications} == {
        user_a.id,
        user_b.id,
    }
