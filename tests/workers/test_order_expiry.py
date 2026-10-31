# tests/workers/test_order_expiry.py
# 未付款訂單過期 worker：created 超時 → cancelled + 歸還庫存 + 取消通知。

from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.events import EventType
from app.models import NotificationOutbox
from app.workers.order_expiry import expire_once


def _created_seconds_ago(seconds: float) -> datetime:
    return datetime.now(timezone.utc) - timedelta(seconds=seconds)


def test_expired_unpaid_order_cancels_and_restores_stock(
    test_db, create_test_user, test_user_data, create_test_order, create_test_product
):
    user = create_test_user(**test_user_data)
    product = create_test_product(stock=9)  # 模擬「建單時已扣 1」的狀態
    order = create_test_order(user.id, product=product, quantity=1)
    order.created_at = _created_seconds_ago(2000)  # 超過預設 1800 秒過期線
    test_db.commit()

    expired = expire_once(test_db)

    test_db.refresh(order)
    test_db.refresh(product)
    assert order.status == "cancelled"
    assert product.stock == 10  # 歸還 1
    assert expired == 1

    # 取消通知走既有 outbox 鏈路。
    event = test_db.scalar(
        select(NotificationOutbox).where(
            NotificationOutbox.event_type == EventType.order_cancelled,
        )
    )
    assert event is not None


def test_recent_unpaid_order_is_untouched(
    test_db, create_test_user, test_user_data, create_test_order, create_test_product
):
    user = create_test_user(**test_user_data)
    product = create_test_product(stock=9)
    order = create_test_order(user.id, product=product, quantity=1)
    order.created_at = _created_seconds_ago(60)  # 還在 1800 秒窗口內
    test_db.commit()

    expired = expire_once(test_db)

    test_db.refresh(order)
    assert order.status == "unpaid"
    assert product.stock == 9
    assert expired == 0


def test_paid_order_is_never_expired(
    test_db, create_test_user, test_user_data, create_test_order, create_test_product
):
    # 只過期 created（未付款）——pending/processing/completed 不受影響。
    user = create_test_user(**test_user_data)
    product = create_test_product(stock=9)
    order = create_test_order(user.id, product=product, status="paid", quantity=1)
    order.created_at = _created_seconds_ago(2000)
    test_db.commit()

    expired = expire_once(test_db)

    test_db.refresh(order)
    assert order.status == "paid"
    assert expired == 0
