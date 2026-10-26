# tests/fixtures/notifications.py

import pytest
from sqlalchemy import delete

from app.models import Notification, NotificationOutbox


@pytest.fixture
def create_test_notification(test_db):
    """建立通知測試資料，並回傳建立好的通知。"""

    def _create_test_notification(user_id: int, **overrides) -> Notification:
        notification = Notification(
            user_id=user_id,
            type=overrides.get("type", "order_status"),
            title=overrides.get("title", "Order updated"),
            body=overrides.get("body", "Your order status has changed."),
            data=overrides.get("data", {}),
            read_at=overrides.get("read_at"),
        )
        test_db.add(notification)
        test_db.flush()
        test_db.refresh(notification)

        return notification

    return _create_test_notification


@pytest.fixture
def clean_outbox(test_db):
    """清空 notification_outbox，讓 outbox 計數斷言只反映本測試。

    共享 test DB 會殘留其他測試（經 dispatch_once / worker commit）的事件，
    dispatcher 的精確計數斷言（dispatched == N）需要乾淨起點。
    """

    def _clean() -> None:
        test_db.execute(delete(NotificationOutbox))
        test_db.commit()

    _clean()
    return _clean
