# tests/orders/integration/test_orders_api.py

import pytest
from rq.exceptions import NoSuchJobError
from rq.job import Job
from rq.registry import FinishedJobRegistry, StartedJobRegistry

from app.core.queue import get_task_publisher
from app.core.rq_publisher import TASK_REGISTRY, default_queue
from app.main import app


@pytest.fixture
def fake_publisher(monkeypatch):
    """用 fake 取代真 publisher（跟 override_get_db 同一招）。

    monkeypatch.setitem 會自動還原：測試結束時，
    若之前已有別的 override 會被裝回去，本來沒有則移除。
    """

    class FakePublisher:
        def __init__(self):
            self.calls = []

        def enqueue(self, task_name, payload):
            self.calls.append((task_name, payload))

            return "fake-job-id"

    fake = FakePublisher()

    monkeypatch.setitem(
        app.dependency_overrides,
        get_task_publisher,
        lambda: fake,
    )

    yield fake


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
    test_user_data,
):
    # 建立 User。
    user = create_test_user(**test_user_data)

    # 登入者可以建立自己的 Order。
    response = auth_client(test_user_data).post("/orders")

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["user_id"] == user.id


def test_create_order_enqueues_notification(
    auth_client,
    create_test_user,
    test_user_data,
    fake_publisher,
):
    # 建立 User。
    create_test_user(**test_user_data)

    # 登入者建立 Order。
    response = auth_client(test_user_data).post("/orders")

    assert response.status_code == 200

    order_id = response.json()["id"]

    # 路由應該用正確的任務名稱與 payload 發布背景任務。
    assert fake_publisher.calls == [
        ("notifications.order_created", {"order_id": order_id}),
    ]


def test_create_order_publishes_to_rq_queue(
    auth_client,
    create_test_user,
    test_user_data,
):
    # 不替換 publisher，驗證真的有 job 進 RQ 佇列。
    # 需要 Redis 可連線（clear_rate_limit autouse fixture 已保證）。
    create_test_user(**test_user_data)

    response = auth_client(test_user_data).post("/orders")

    assert response.status_code == 200

    order_id = response.json()["id"]

    # 本機可能正在跑 worker，job 會在斷言前被領走甚至執行完畢，
    # 所以不能只看佇列長度：把「排隊中、執行中、已完成」
    # 三個生命週期都掃過，找符合的 job，與 worker 速度無關。
    candidate_ids = list(default_queue.job_ids)

    for registry in (
        StartedJobRegistry(queue=default_queue),
        FinishedJobRegistry(queue=default_queue),
    ):
        candidate_ids.extend(registry.get_job_ids())

    matching = []

    for job_id in candidate_ids:
        try:
            job = Job.fetch(job_id, connection=default_queue.connection)
        except NoSuchJobError:
            # job 已過期被清掉，跳過。
            continue

        if job.func_name == TASK_REGISTRY[
            "notifications.order_created"
        ] and job.kwargs == {"payload": {"order_id": order_id}}:
            matching.append(job_id)

    assert matching, f"no RQ job found for order_id={order_id}"


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
