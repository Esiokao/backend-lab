import pytest
from sqlalchemy import func, select

from app.models import Notification
from app.workers.notifications import notify_order_created


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
