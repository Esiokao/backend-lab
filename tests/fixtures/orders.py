# tests/fixtures/orders.py

import pytest

from app.models import Order


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
