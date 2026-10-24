# tests/orders/integration/test_order_cancel.py
# POST /orders/{id}/cancel：擁有者取消；狀態機僅 created/pending 可取消。


def test_owner_can_cancel_created_order(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
):
    user = create_test_user(**test_user_data)
    order = create_test_order(user_id=user.id, status="created")
    client = session_auth_client(test_user_data)

    response = client.post(f"/orders/{order.id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_owner_can_cancel_pending_order(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
):
    user = create_test_user(**test_user_data)
    order = create_test_order(user_id=user.id, status="pending")
    client = session_auth_client(test_user_data)

    response = client.post(f"/orders/{order.id}/cancel")

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cannot_cancel_completed_order(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
):
    user = create_test_user(**test_user_data)
    order = create_test_order(user_id=user.id, status="completed")
    client = session_auth_client(test_user_data)

    response = client.post(f"/orders/{order.id}/cancel")

    assert response.status_code == 400
    assert "cannot be cancelled" in response.json()["detail"]


def test_cannot_cancel_cancelled_order_again(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
):
    user = create_test_user(**test_user_data)
    order = create_test_order(user_id=user.id, status="cancelled")
    client = session_auth_client(test_user_data)

    response = client.post(f"/orders/{order.id}/cancel")

    assert response.status_code == 400


def test_cannot_cancel_another_users_order(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
    test_random_user_data,
):
    owner = create_test_user(**test_user_data)
    order = create_test_order(user_id=owner.id)

    create_test_user(**test_random_user_data)
    client = session_auth_client(test_random_user_data)

    response = client.post(f"/orders/{order.id}/cancel")

    assert response.status_code == 404


def test_unauthenticated_cannot_cancel(
    test_client, create_test_user, create_test_order, test_user_data
):
    user = create_test_user(**test_user_data)
    order = create_test_order(user_id=user.id)

    response = test_client.post(f"/orders/{order.id}/cancel")

    assert response.status_code == 401
