# tests/test_get_orders.py


def test_get_orders(test_client):
    # 可以取得 Order 列表。
    response = test_client.get("/orders")

    assert response.status_code == 200


def test_get_orders_pagination(test_client):
    # Pagination 限制每頁最多回傳 5 筆。
    response = test_client.get("/orders?page=1&page_size=5")

    assert response.status_code == 200
    assert len(response.json()) <= 5


def test_get_orders_filter_by_user(test_client, test_order):
    # 只取得指定 User 的 Orders。
    response = test_client.get(f"/orders?user_id={test_order.user_id}")

    assert response.status_code == 200

    orders = response.json()

    assert len(orders) > 0

    for order in orders:
        assert order["user_id"] == test_order.user_id


def test_get_orders_sort_desc(test_client):
    # 確認可以按照 Order ID 由大到小排序。
    response = test_client.get("/orders?sort_by=id&order=desc")

    assert response.status_code == 200

    orders = response.json()
    ids = [order["id"] for order in orders]

    assert ids == sorted(ids, reverse=True)


def test_get_orders_invalid_page(test_client):
    # page 不可以小於 1。
    response = test_client.get("/orders?page=0")

    assert response.status_code == 422


def test_get_orders_invalid_page_size(test_client):
    # page_size 不可以大於 100。
    response = test_client.get("/orders?page_size=101")

    assert response.status_code == 422


def test_get_order_owner(
    auth_client,
    test_user_data,
    test_user,
    test_order,
):
    # 登入者可以取得自己的 Order。
    response = auth_client(test_user_data).get(f"/orders/{test_order.id}")

    assert response.status_code == 200

    order = response.json()

    assert order["id"] == test_order.id
    assert order["user_id"] == test_order.user_id


def test_get_order_other_user(
    auth_client,
    test_user_data,
    test_user,
    test_other_order,
):
    # 登入者不能取得其他 User 的 Order。
    response = auth_client(test_user_data).get(f"/orders/{test_other_order.id}")

    assert response.status_code == 404


def test_get_order_unauthenticated(test_client, test_order):
    # 未登入者不能取得 Order。
    response = test_client.get(f"/orders/{test_order.id}")

    assert response.status_code == 401


def test_create_order_unauthenticated(test_client):
    # 未登入者不能建立 Order。
    response = test_client.post("/orders")

    assert response.status_code == 401


def test_create_order_owner(
    auth_client,
    test_user_data,
    test_user,
):
    # 登入者可以建立自己的 Order。
    response = auth_client(test_user_data).post("/orders")

    assert response.status_code == 200

    response_data = response.json()

    assert response_data["user_id"] == test_user.id

    print(">>> TEST FINISHED")
