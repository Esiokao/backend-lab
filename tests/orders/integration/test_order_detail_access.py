# tests/orders/integration/test_order_detail_access.py
# GET /orders/{id} 讀取權限：擁有者或 admin；非擁有者 404。

from app.models import Order


def test_owner_can_read_own_order(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
):
    user = create_test_user(**test_user_data)
    order = create_test_order(user_id=user.id, quantity=2)

    client = session_auth_client(test_user_data)
    response = client.get(f"/orders/{order.id}")

    assert response.status_code == 200
    body = response.json()
    assert body["id"] == order.id
    assert body["user_id"] == user.id
    assert len(body["items"]) == 1


def test_non_owner_cannot_read_order(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
    test_random_user_data,
):
    owner = create_test_user(**test_user_data)
    order = create_test_order(user_id=owner.id)

    _stranger = create_test_user(**test_random_user_data)
    client = session_auth_client(test_random_user_data)

    # 非擁有者讀別人的訂單 → 404（與不存在同回應，不洩露存在性）。
    response = client.get(f"/orders/{order.id}")
    assert response.status_code == 404


def test_admin_can_read_any_users_order(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_admin_user_data,
    test_user_data,
):
    create_test_user(**test_admin_user_data)
    user = create_test_user(**test_user_data)
    order = create_test_order(user_id=user.id)

    client = session_auth_client(test_admin_user_data)
    response = client.get(f"/orders/{order.id}")

    assert response.status_code == 200
    assert response.json()["id"] == order.id


def test_admin_404_for_missing_order(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
):
    create_test_user(**test_admin_user_data)
    client = session_auth_client(test_admin_user_data)

    response = client.get("/orders/999999")
    assert response.status_code == 404


def test_unauthenticated_cannot_read_order(
    test_client,
    create_test_user,
    create_test_order,
    test_user_data,
):
    user = create_test_user(**test_user_data)
    order: Order = create_test_order(user_id=user.id)

    response = test_client.get(f"/orders/{order.id}")
    assert response.status_code == 401
