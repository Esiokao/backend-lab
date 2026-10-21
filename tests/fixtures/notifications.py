# tests/fixtures/notifications.py

import pytest

from app.models import Notification


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
