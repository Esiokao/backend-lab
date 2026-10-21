# tests/fixtures/orders.py

import pytest

from app.models import Order
from app.core.events import ORDER_CREATED


@pytest.fixture
def create_test_order(test_db):
    # 建立 Order 的 factory。
    def _create_order(user_id):
        order = Order(
            user_id=user_id,
        )

        test_db.add(order)
        test_db.flush()
        test_db.refresh(order)

        return order

    return _create_order


@pytest.fixture
def create_test_outbox_event(test_db):
    """建立 Outbox 測試事件。"""

    def _create_event(
        *,
        event_type=ORDER_CREATED,
        payload,
    ):
        from app.models import NotificationOutbox

        event = NotificationOutbox(
            event_type=event_type,
            payload=payload,
        )
        test_db.add(event)
        test_db.flush()
        test_db.refresh(event)
        return event

    return _create_event
