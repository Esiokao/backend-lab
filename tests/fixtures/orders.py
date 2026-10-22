# tests/fixtures/orders.py

import pytest

from app.core.events import ORDER_CREATED
from app.models import Order


@pytest.fixture
def create_test_order(test_db, create_test_product):
    """建立 Order 的 factory。

    新契約：orders.product_id / quantity 為 NOT NULL，
    所以每次都先建一個測試商品（除非呼叫端指定）。
    """

    def _create_order(
        user_id,
        *,
        status: str = "pending",
        product=None,
        quantity: int = 1,
        stock: int = 10,
    ):
        # 未指定商品時，建立一個庫存充足的測試商品供此訂單引用。
        product = product or create_test_product(stock=max(stock, quantity))

        order = Order(
            user_id=user_id,
            product_id=product.id,
            status=status,
            quantity=quantity,
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
