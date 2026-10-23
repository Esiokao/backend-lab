# tests/orders/integration/test_orders_api.py

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.core.events import EventType
from app.core.outbox_dispatcher import dispatch_once
from app.models import NotificationOutbox, Product


class FakePublisher:
    """記錄 enqueue 呼叫的假 publisher。"""

    def __init__(self):
        self.calls = []

    def enqueue(self, task_name, payload):
        self.calls.append((task_name, payload))

        return "fake-job-id"


@pytest.fixture
def fake_publisher():
    """假 publisher：直接以參數傳給 dispatch_once（依賴在簽名裡，免 monkeypatch）。"""
    return FakePublisher()


def test_create_order_with_product_decreases_stock(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    _user = create_test_user(**test_user_data)

    product = Product(
        name="Coffee Beans",
        price=Decimal("19.99"),
        stock=10,
        is_active=True,
    )
    test_db.add(product)
    test_db.flush()

    auth_client = session_auth_client(test_user_data)

    response = auth_client.post(
        "/orders",
        json={
            "items": [
                {"product_id": product.id, "quantity": 3},
            ],
        },
    )

    assert response.status_code == 200

    test_db.refresh(product)

    # 建立訂單後，庫存應減少購買數量。
    assert product.stock == 7

    # 回應的明細應帶商品與數量。
    items = response.json()["items"]

    assert len(items) == 1
    assert items[0]["product_id"] == product.id
    assert items[0]["quantity"] == 3


def test_get_orders_unauthenticated(test_client):
    # 未登入不能取得訂單列表。
    response = test_client.get("/orders")

    assert response.status_code == 401


def test_get_orders(auth_client, create_test_user, test_user_data):
    # 登入後可以取得自己的 Order 列表。
    create_test_user(**test_user_data)
    client = auth_client(test_user_data)

    response = client.get("/orders")

    assert response.status_code == 200
    assert len(response.json()) >= 0


def test_get_orders_pagination(auth_client, create_test_user, test_user_data):
    # Pagination 限制每頁最多回傳 5 筆。
    create_test_user(**test_user_data)
    client = auth_client(test_user_data)

    response = client.get("/orders?page=1&page_size=5")

    assert response.status_code == 200
    assert len(response.json()) <= 5


def test_get_orders_filter_by_user(
    auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
    create_test_product,
):
    # 建立 User 與屬於他的 Order，查詢自己的（user_id 參數對自己無害）。
    user = create_test_user(**test_user_data)
    order = create_test_order(user.id)
    client = auth_client(test_user_data)

    response = client.get(f"/orders?user_id={order.user_id}")

    assert response.status_code == 200

    orders = response.json()

    assert len(orders) > 0
    assert all(item["user_id"] == user.id for item in orders)


def test_get_orders_sort_desc(auth_client, create_test_user, test_user_data):
    # 確認可以按照 Order ID 由大到小排序。
    create_test_user(**test_user_data)
    client = auth_client(test_user_data)

    response = client.get("/orders?sort_by=id&order=desc")

    assert response.status_code == 200

    orders = response.json()
    ids = [order["id"] for order in orders]

    assert ids == sorted(ids, reverse=True)


def test_get_orders_invalid_page(auth_client, create_test_user, test_user_data):
    # page 不可以小於 1。
    create_test_user(**test_user_data)
    client = auth_client(test_user_data)

    response = client.get("/orders?page=0")

    assert response.status_code == 422


def test_get_orders_invalid_page_size(auth_client, create_test_user, test_user_data):
    # page_size 不可以大於 100。
    create_test_user(**test_user_data)
    client = auth_client(test_user_data)

    response = client.get("/orders?page_size=101")

    assert response.status_code == 422


def test_user_sees_only_own_orders(
    auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
    test_random_user_data,
):
    # 一般使用者只能看到自己的訂單，看不到其他人的。
    user = create_test_user(**test_user_data)
    other = create_test_user(**test_random_user_data)

    own_order = create_test_order(user.id)
    create_test_order(other.id)

    client = auth_client(test_user_data)
    response = client.get("/orders")

    assert response.status_code == 200

    orders = response.json()
    assert len(orders) == 1
    assert orders[0]["id"] == own_order.id


def test_get_order_owner(
    auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
):
    # 建立 User。
    user = create_test_user(**test_user_data)

    # 建立屬於 User 的 Order。
    order = create_test_order(user.id)

    # 登入者可以取得自己的 Order。
    response = auth_client(test_user_data).get(f"/orders/{order.id}")

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["id"] == order.id
    assert response_data["user_id"] == user.id


def test_get_order_other_user(
    auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
    test_random_user_data,
):
    # 建立登入者。
    create_test_user(**test_user_data)

    # 建立另一個 User。
    other_user = create_test_user(**test_random_user_data)

    # 建立屬於另一個 User 的 Order。
    other_order = create_test_order(other_user.id)

    # 登入者不能取得其他 User 的 Order。
    response = auth_client(test_user_data).get(f"/orders/{other_order.id}")

    # 應該回傳 404。
    assert response.status_code == 404


def test_get_order_unauthenticated(
    test_client,
    create_test_user,
    create_test_order,
    test_user_data,
):
    # 建立 User。
    user = create_test_user(**test_user_data)

    # 建立 User 的 Order。
    order = create_test_order(user.id)

    # 未登入者不能取得 Order。
    response = test_client.get(f"/orders/{order.id}")

    assert response.status_code == 401


def test_create_order_unauthenticated(test_client):
    # 未登入者不能建立 Order。
    response = test_client.post("/orders")

    assert response.status_code == 401


def test_create_order_owner(
    auth_client,
    create_test_user,
    create_test_product,
    test_user_data,
):
    # 建立 User 與商品。
    user = create_test_user(**test_user_data)
    product = create_test_product(stock=5)

    # 登入者可以建立自己的 Order（帶商品與數量）。
    response = auth_client(test_user_data).post(
        "/orders",
        json={
            "items": [
                {"product_id": product.id, "quantity": 2},
            ],
        },
    )

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["user_id"] == user.id

    items = response_data["items"]

    assert len(items) == 1
    assert items[0]["product_id"] == product.id
    assert items[0]["quantity"] == 2


def test_create_order_writes_outbox_event(
    auth_client,
    create_test_user,
    create_test_product,
    test_user_data,
    test_db,
):
    # 建立使用者與商品，並下訂單。
    create_test_user(**test_user_data)
    product = create_test_product(stock=5)
    client = auth_client(test_user_data)

    response = client.post(
        "/orders",
        json={
            "items": [
                {"product_id": product.id, "quantity": 1},
            ],
        },
    )

    assert response.status_code == 200

    order_id = response.json()["id"]

    # 訂單與 outbox 事件在同一個交易寫入：
    # 事件應已存在、待處理，且 payload 帶著訂單 ID。
    event = test_db.scalar(
        select(NotificationOutbox).where(
            NotificationOutbox.event_type == EventType.order_created
        )
    )

    assert event is not None
    assert event.payload == {"order_id": order_id}
    assert event.status == "pending"


def test_outbox_dispatcher_publishes_pending_events(
    auth_client,
    create_test_user,
    create_test_product,
    test_user_data,
    test_db,
    fake_publisher,
):
    # 建立商品並下訂單（同交易寫入 outbox 事件）。
    product = create_test_product(stock=5)
    create_test_user(**test_user_data)
    client = auth_client(test_user_data)

    response = client.post(
        "/orders",
        json={
            "items": [
                {"product_id": product.id, "quantity": 1},
            ],
        },
    )

    assert response.status_code == 200

    order_id = response.json()["id"]

    # dispatcher 跑一輪：挑選 pending 事件 → 富化 payload → 標記 dispatched。
    dispatched = dispatch_once(test_db, publisher=fake_publisher)

    assert dispatched == 1

    assert len(fake_publisher.calls) == 1

    task_name, payload = fake_publisher.calls[0]

    assert task_name == EventType.order_created
    assert payload["order_id"] == order_id
    assert isinstance(payload["outbox_event_id"], int)

    # 事件應被標記為 dispatched（已交給佇列，不代表通知已完成）。
    event = test_db.scalar(
        select(NotificationOutbox).where(
            NotificationOutbox.event_type == EventType.order_created
        )
    )

    assert event is not None
    assert event.status == "dispatched"
    assert event.attempts == 1


def test_dispatcher_skips_events_within_visibility_timeout(
    auth_client,
    create_test_user,
    create_test_product,
    test_user_data,
    test_db,
    fake_publisher,
):
    # 建立商品並下訂單（outbox 事件）→ 手動標記 dispatched + 未來的可見時間。
    product = create_test_product(stock=5)
    create_test_user(**test_user_data)
    client = auth_client(test_user_data)

    response = client.post(
        "/orders",
        json={
            "items": [
                {"product_id": product.id, "quantity": 1},
            ],
        },
    )

    assert response.status_code == 200

    event = test_db.scalar(
        select(NotificationOutbox).where(
            NotificationOutbox.event_type == EventType.order_created
        )
    )

    event.status = "dispatched"
    event.available_at = datetime.now(timezone.utc) + timedelta(seconds=60)
    test_db.commit()

    # 還在 visibility timeout 內的事件不應重複發佈。
    dispatched = dispatch_once(test_db, publisher=fake_publisher)

    assert dispatched == 0
    assert fake_publisher.calls == []


def test_get_other_user_orders(
    auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
    test_random_user_data,
):
    # 建立登入者。
    create_test_user(**test_user_data)

    # 建立另一個 User。
    other_user = create_test_user(**test_random_user_data)

    # 建立另一個 User 的 Order。
    create_test_order(other_user.id)

    # 登入者不能查看其他 User 的 Orders。
    client = auth_client(test_user_data)

    response = client.get(f"/users/{other_user.id}/orders")

    assert response.status_code == 403


def test_get_own_user_orders(
    auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
):
    # 建立 User。
    user = create_test_user(**test_user_data)

    # 建立 User 的 Order。
    create_test_order(user.id)

    # 查看自己的 Orders。
    client = auth_client(test_user_data)

    response = client.get(f"/users/{user.id}/orders")

    assert response.status_code == 200

    orders = response.json()

    assert len(orders) > 0
    assert all(order["user_id"] == user.id for order in orders)


def test_get_users_with_orders_forbidden(
    auth_client,
    create_test_user,
    test_user_data,
):
    # 建立一般 User。
    create_test_user(**test_user_data)

    # 一般 User 登入。
    client = auth_client(test_user_data)

    # 一般 User 嘗試查看所有 Users 的 Orders。
    response = client.get("/users-with-orders")

    # 只有 admin 可以存取。
    assert response.status_code == 403


def test_get_other_users_order_forbidden(
    create_test_user, create_test_order, test_user_data, auth_client
):
    # create user A
    create_test_user(**test_user_data)
    user_b = create_test_user()

    order = create_test_order(user_b.id)

    # login with user A data
    client_a = auth_client(test_user_data)

    response = client_a.get(f"/orders/{order.id}")

    assert response.status_code == 404


def test_get_order_with_invalid_token(
    test_client,
    create_test_user,
    create_test_order,
    test_user_data,
):
    # 建立測試 User。
    user = create_test_user(**test_user_data)

    # 建立 User 的 Order。
    order = create_test_order(user.id)

    # 使用無效的 JWT。
    test_client.headers.update({"Authorization": "Bearer invalid-token"})

    # 嘗試取得 Order。
    response = test_client.get(f"/orders/{order.id}")

    # 無效 JWT 應該被拒絕。
    assert response.status_code == 401
