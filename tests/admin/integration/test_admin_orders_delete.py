# tests/admin/integration/test_admin_orders_delete.py
# 測試 Admin 訂單刪除：成功、不存在與權限驗證。

from app.models import Order


def test_admin_can_delete_order(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
):
    """Admin 可以刪除存在的訂單。"""
    # 建立管理員與訂單擁有者。
    create_test_user(**test_admin_user_data)
    owner = create_test_user(**test_user_data)

    # 建立待刪除的訂單。
    order = Order(user_id=owner.id, status="pending")
    test_db.add(order)
    test_db.commit()
    test_db.refresh(order)
    order_id = order.id

    # 使用管理員身分刪除訂單。
    client = session_auth_client(test_admin_user_data)
    response = client.delete(f"/admin/orders/{order_id}")

    assert response.status_code == 204
    assert test_db.get(Order, order_id) is None


def test_admin_cannot_delete_nonexistent_order(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
):
    """Admin 刪除不存在的訂單時，回傳 404。"""
    create_test_user(**test_admin_user_data)
    client = session_auth_client(test_admin_user_data)

    response = client.delete("/admin/orders/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_session_user_cannot_delete_order(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
):
    """一般登入使用者不能刪除訂單。"""
    # 建立管理員與訂單擁有者。
    create_test_user(**test_admin_user_data)
    owner = create_test_user(**test_user_data)

    # 建立訂單並保留主鍵。
    order = Order(user_id=owner.id, status="pending")
    test_db.add(order)
    test_db.commit()
    test_db.refresh(order)
    order_id = order.id

    # 一般使用者嘗試刪除訂單。
    client = session_auth_client(test_user_data)
    response = client.delete(f"/admin/orders/{order_id}")

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"
    assert test_db.get(Order, order_id) is not None


def test_unauthenticated_user_cannot_delete_order(
    test_client,
    create_test_user,
    test_user_data,
    test_db,
):
    """未登入使用者不能刪除訂單。"""
    owner = create_test_user(**test_user_data)

    # 建立訂單。
    order = Order(user_id=owner.id, status="pending")
    test_db.add(order)
    test_db.commit()
    test_db.refresh(order)
    order_id = order.id

    # 未登入的請求應被拒絕。
    response = test_client.delete(f"/admin/orders/{order_id}")

    assert response.status_code == 401
    assert test_db.get(Order, order_id) is not None
