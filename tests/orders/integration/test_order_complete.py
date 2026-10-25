# tests/orders/integration/test_order_complete.py
# POST /orders/{id}/complete（v1.18）：admin 將 pending 訂單標記完成；
# 狀態機把關（僅 pending 可完成）＋ Outbox 事件（worker 發通知）。

from sqlalchemy import select

from app.core.events import EventType
from app.models import NotificationOutbox


def test_admin_can_complete_pending_order(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_admin_user_data,
    test_user_data,
    test_db,
):
    create_test_user(**test_admin_user_data)
    buyer = create_test_user(**test_user_data)
    order = create_test_order(user_id=buyer.id, status="pending")
    test_db.commit()

    client = session_auth_client(test_admin_user_data)
    response = client.post(f"/orders/{order.id}/complete")

    assert response.status_code == 200
    assert response.json()["status"] == "completed"

    # 同一交易寫入 order_completed Outbox 事件（worker 接手發通知）。
    event = test_db.scalar(
        select(NotificationOutbox).where(
            NotificationOutbox.event_type == EventType.order_completed
        )
    )
    assert event is not None
    assert event.payload == {"order_id": order.id}


def test_cannot_complete_created_order(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_admin_user_data,
    test_user_data,
):
    # 未付款（created）不能直接完成——狀態機要求先付款。
    create_test_user(**test_admin_user_data)
    buyer = create_test_user(**test_user_data)
    order = create_test_order(user_id=buyer.id, status="created")

    client = session_auth_client(test_admin_user_data)
    response = client.post(f"/orders/{order.id}/complete")

    assert response.status_code == 400
    assert "cannot be completed" in response.json()["detail"]


def test_cannot_complete_cancelled_order(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_admin_user_data,
    test_user_data,
):
    create_test_user(**test_admin_user_data)
    buyer = create_test_user(**test_user_data)
    order = create_test_order(user_id=buyer.id, status="cancelled")

    client = session_auth_client(test_admin_user_data)
    response = client.post(f"/orders/{order.id}/complete")

    assert response.status_code == 400


def test_non_admin_cannot_complete_order(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
):
    buyer = create_test_user(**test_user_data)
    order = create_test_order(user_id=buyer.id, status="pending")

    client = session_auth_client(test_user_data)
    response = client.post(f"/orders/{order.id}/complete")

    assert response.status_code == 403


def test_complete_missing_order_returns_404(
    session_auth_client, create_test_user, test_admin_user_data
):
    create_test_user(**test_admin_user_data)
    client = session_auth_client(test_admin_user_data)

    response = client.post("/orders/999999999/complete")

    assert response.status_code == 404
