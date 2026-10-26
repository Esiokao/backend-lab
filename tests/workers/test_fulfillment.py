# tests/workers/test_fulfillment.py
# 履約模擬 worker：paid（pending）→ processing → completed，
# completed 與 order_completed Outbox 事件同一交易寫入。

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.events import EventType
from app.models import NotificationOutbox
from app.workers.fulfillment import advance_once


def _paid_seconds_ago(seconds: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


def test_paid_order_advances_to_processing(
    test_db, create_test_user, test_user_data, create_test_order
):
    user = create_test_user(**test_user_data)
    order = create_test_order(user_id=user.id, status="pending")
    order.paid_at = _paid_seconds_ago(10)  # 超過預設 5 秒 processing 延遲
    test_db.commit()

    advanced = advance_once(test_db)

    test_db.refresh(order)
    assert order.status == "processing"
    assert advanced == 1


def test_matured_order_completes_with_outbox_event(
    test_db, create_test_user, test_user_data, create_test_order
):
    user = create_test_user(**test_user_data)
    order = create_test_order(user_id=user.id, status="processing")
    order.paid_at = _paid_seconds_ago(100)  # 超過預設 65 秒完成延遲
    test_db.commit()

    advanced = advance_once(test_db)

    test_db.refresh(order)
    assert order.status == "completed"
    assert advanced == 1

    # completed 與 outbox 事件同一交易：通知走既有 worker 鏈路。
    event = test_db.scalar(
        select(NotificationOutbox).where(
            NotificationOutbox.event_type == EventType.order_completed,
            NotificationOutbox.payload["order_id"].as_integer() == order.id,
        )
    )
    assert event is not None


def test_recent_paid_order_is_untouched(
    test_db, create_test_user, test_user_data, create_test_order
):
    user = create_test_user(**test_user_data)
    order = create_test_order(user_id=user.id, status="pending")
    order.paid_at = _paid_seconds_ago(1)  # 還沒到 5 秒
    test_db.commit()

    advance_once(test_db)

    test_db.refresh(order)
    assert order.status == "pending"


def test_unpaid_and_terminal_orders_are_untouched(
    test_db, create_test_user, test_user_data, create_test_order
):
    user = create_test_user(**test_user_data)
    created_at_old = _paid_seconds_ago(1000)

    unpaid = create_test_order(user_id=user.id, status="created")
    cancelled = create_test_order(user_id=user.id, status="cancelled")
    # 未付款訂單不該被 paid_at 以外的時間欄位誤撈：paid_at 維持 None。
    test_db.commit()

    advance_once(test_db, now=created_at_old + timedelta(seconds=500))

    test_db.refresh(unpaid)
    test_db.refresh(cancelled)
    assert unpaid.status == "created"
    assert cancelled.status == "cancelled"
