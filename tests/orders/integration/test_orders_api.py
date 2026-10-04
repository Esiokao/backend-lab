# tests/orders/integration/test_orders_api.py


def test_get_orders(test_client):
    # 可以取得 Order 列表。
    response = test_client.get("/orders")

    assert response.status_code == 200


def test_get_orders_pagination(test_client):
    # Pagination 限制每頁最多回傳 5 筆。
    response = test_client.get("/orders?page=1&page_size=5")

    assert response.status_code == 200
    assert len(response.json()) <= 5


def test_get_orders_filter_by_user(
    test_client,
    create_test_user,
    create_test_order,
    test_user_data,
):
    # 建立 User。
    user = create_test_user(**test_user_data)

    # 建立屬於 User 的 Order。
    order = create_test_order(user.id)

    # 只取得指定 User 的 Orders。
    response = test_client.get(f"/orders?user_id={order.user_id}")

    assert response.status_code == 200

    orders = response.json()

    assert len(orders) > 0
    assert all(item["user_id"] == user.id for item in orders)


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
