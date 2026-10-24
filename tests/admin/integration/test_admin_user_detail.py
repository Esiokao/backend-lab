# tests/admin/integration/test_admin_user_detail.py
# GET /admin/users/{id}：admin 檢視使用者詳情（基本資料 + 訂單）。


def test_admin_can_view_user_detail_with_orders(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_admin_user_data,
    test_user_data,
):
    create_test_user(**test_admin_user_data)
    target = create_test_user(**test_user_data)
    order_a = create_test_order(user_id=target.id, quantity=1)
    order_b = create_test_order(user_id=target.id, quantity=3)

    client = session_auth_client(test_admin_user_data)
    response = client.get(f"/admin/users/{target.id}")

    assert response.status_code == 200
    body = response.json()

    assert body["user"]["id"] == target.id
    assert body["user"]["email"] == target.email
    assert len(body["orders"]) == 2
    # 新訂單在前（id 降冪）。
    assert [o["id"] for o in body["orders"]] == [order_b.id, order_a.id]
    # 訂單含明細（unit_price 快照）。
    assert body["orders"][0]["items"][0]["quantity"] == 3


def test_admin_user_detail_404_for_unknown_user(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
):
    create_test_user(**test_admin_user_data)
    client = session_auth_client(test_admin_user_data)

    response = client.get("/admin/users/999999")
    assert response.status_code == 404


def test_non_admin_cannot_view_user_detail(
    session_auth_client,
    create_test_user,
    test_user_data,
    test_random_user_data,
):
    create_test_user(**test_user_data)
    stranger = create_test_user(**test_random_user_data)

    client = session_auth_client(test_random_user_data)
    response = client.get(f"/admin/users/{stranger.id}")

    assert response.status_code == 403


def test_unauthenticated_cannot_view_user_detail(test_client):
    response = test_client.get("/admin/users/1")
    assert response.status_code == 401
