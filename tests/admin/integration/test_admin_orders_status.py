# tests/admin/integration/test_admin_orders_status.py
# 測試 Admin 訂單狀態機、權限、輸入驗證與資料庫狀態。

import pytest

from app.models import Order, Product


def create_order(test_db, owner, order_status):
    """建立指定初始狀態的訂單（含一個測試商品供引用）。"""
    product = Product(name=f"Product for {owner.email}", price=19.99, stock=10)
    test_db.add(product)
    test_db.flush()

    order = Order(
        user_id=owner.id,
        status=order_status,
        product_id=product.id,
        quantity=1,
    )
    test_db.add(order)
    test_db.commit()
    test_db.refresh(order)
    return order


def test_admin_can_update_order_status(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
):
    """Admin 可以將 pending 訂單更新為 processing。"""
    create_test_user(**test_admin_user_data)
    owner = create_test_user(**test_user_data)
    order = create_order(test_db, owner, "pending")
    order_id = order.id

    client = session_auth_client(test_admin_user_data)
    response = client.patch(
        f"/admin/orders/{order_id}/status",
        params={"new_status": "processing"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == order_id
    assert response.json()["status"] == "processing"

    # 確認資料庫中的狀態也已更新。
    test_db.expire_all()
    updated_order = test_db.get(Order, order_id)
    assert updated_order is not None
    assert updated_order.status == "processing"


@pytest.mark.parametrize(
    ("initial_status", "new_status"),
    [
        ("pending", "processing"),
        ("pending", "cancelled"),
        ("processing", "completed"),
        ("processing", "cancelled"),
    ],
)
def test_admin_can_make_valid_status_transitions(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
    initial_status,
    new_status,
):
    """Admin 可以執行所有允許的狀態轉換。"""
    create_test_user(**test_admin_user_data)
    owner = create_test_user(**test_user_data)
    order = create_order(test_db, owner, initial_status)
    order_id = order.id

    client = session_auth_client(test_admin_user_data)
    response = client.patch(
        f"/admin/orders/{order_id}/status",
        params={"new_status": new_status},
    )

    assert response.status_code == 200
    assert response.json()["status"] == new_status

    test_db.expire_all()
    updated_order = test_db.get(Order, order_id)
    assert updated_order is not None
    assert updated_order.status == new_status


@pytest.mark.parametrize(
    ("initial_status", "new_status"),
    [
        ("pending", "completed"),
        ("pending", "pending"),  # 不允許重複設定相同狀態
        ("processing", "pending"),
        ("processing", "processing"),  # 不允許重複設定相同狀態
        ("completed", "pending"),
        ("completed", "processing"),
        ("completed", "cancelled"),
        ("cancelled", "pending"),
        ("cancelled", "processing"),
        ("cancelled", "completed"),
        ("cancelled", "cancelled"),
    ],
)
def test_admin_cannot_make_invalid_status_transitions(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
    initial_status,
    new_status,
):
    """非法狀態轉換應回傳 409，且資料庫狀態保持不變。"""
    create_test_user(**test_admin_user_data)
    owner = create_test_user(**test_user_data)
    order = create_order(test_db, owner, initial_status)
    order_id = order.id

    client = session_auth_client(test_admin_user_data)
    response = client.patch(
        f"/admin/orders/{order_id}/status",
        params={"new_status": new_status},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        f"Cannot change order status from {initial_status} to {new_status}"
    )

    # 重新載入資料，確認非法操作沒有改變狀態。
    test_db.expire_all()
    unchanged_order = test_db.get(Order, order_id)
    assert unchanged_order is not None
    assert unchanged_order.status == initial_status


def test_admin_cannot_update_nonexistent_order(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
):
    """更新不存在的訂單時，回傳 404。"""
    create_test_user(**test_admin_user_data)
    client = session_auth_client(test_admin_user_data)

    response = client.patch(
        "/admin/orders/999999/status",
        params={"new_status": "processing"},
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "Order not found"


def test_unauthenticated_user_cannot_update_order_status(test_client):
    """未登入使用者不能更新訂單狀態。"""
    response = test_client.patch(
        "/admin/orders/999999/status",
        params={"new_status": "processing"},
    )

    assert response.status_code == 401


def test_session_user_cannot_update_order_status(
    session_auth_client,
    create_test_user,
    test_user_data,
):
    """一般登入使用者不能更新管理員訂單狀態。"""
    create_test_user(**test_user_data)
    client = session_auth_client(test_user_data)

    response = client.patch(
        "/admin/orders/999999/status",
        params={"new_status": "processing"},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


@pytest.mark.parametrize(
    "new_status",
    [
        "unknown",
        "PENDING",
        "",
    ],
)
def test_admin_cannot_submit_invalid_status_value(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    new_status,
):
    """不在允許清單中的狀態值應由 API 驗證拒絕。"""
    create_test_user(**test_admin_user_data)
    client = session_auth_client(test_admin_user_data)

    response = client.patch(
        "/admin/orders/999999/status",
        params={"new_status": new_status},
    )

    assert response.status_code == 422
