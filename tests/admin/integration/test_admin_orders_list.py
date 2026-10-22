# tests/admin/integration/test_admin_orders_list.py
# Admin 訂單列表：清單、權限、過濾、分頁。

import pytest


def test_admin_can_list_orders(
    auth_client,
    create_test_user,
    test_admin_user_data,
):
    # 建立管理員帳號。
    create_test_user(**test_admin_user_data)

    # 使用現有的登入 fixture 建立已登入的 client。
    client = auth_client(test_admin_user_data)

    # 管理員取得訂單列表。
    response = client.get("/admin/orders/")

    assert response.status_code == 200

    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data


def test_session_user_cannot_list_admin_orders(
    session_auth_client,
    create_test_user,
    test_user_data,
):
    # 建立一般使用者並透過 Session 登入。
    create_test_user(**test_user_data)
    client = session_auth_client(test_user_data)

    # 一般使用者嘗試取得管理員訂單列表。
    response = client.get("/admin/orders/")

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_session_admin_can_list_orders(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
):
    # 建立管理員並透過 Session 登入。
    create_test_user(**test_admin_user_data)
    client = session_auth_client(test_admin_user_data)

    # 管理員取得訂單列表。
    response = client.get("/admin/orders/")

    assert response.status_code == 200
    assert "items" in response.json()


def test_admin_can_filter_orders_by_status(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
    create_test_order,
):
    # 建立管理員與訂單擁有者。
    create_test_user(**test_admin_user_data)
    owner = create_test_user(**test_user_data)

    # 建立兩筆不同狀態的訂單。
    create_test_order(owner.id, status="pending")
    create_test_order(owner.id, status="processing")
    test_db.commit()

    # 管理員透過 Session 登入。
    client = session_auth_client(test_admin_user_data)

    # 只查詢 pending 訂單。
    response = client.get(
        "/admin/orders/",
        params={"status": "pending"},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["status"] == "pending"


def test_admin_can_filter_orders_by_user_id(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
    create_test_order,
):
    # 建立管理員與兩位一般使用者。
    create_test_user(**test_admin_user_data)
    owner_a = create_test_user(**test_user_data)

    # 第二位使用者使用不同 email。
    user_b_data = {
        **test_user_data,
        "email": "another@example.com",
    }
    owner_b = create_test_user(**user_b_data)

    # 每位使用者各建立一筆訂單。
    create_test_order(owner_a.id, status="pending")
    create_test_order(owner_b.id, status="pending")
    test_db.commit()

    # 管理員透過 Session 登入。
    client = session_auth_client(test_admin_user_data)

    # 只查詢 owner_a 的訂單。
    response = client.get(
        "/admin/orders/",
        params={"user_id": owner_a.id},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["user_id"] == owner_a.id


def test_admin_can_paginate_orders(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
    create_test_order,
):
    # 建立管理員與訂單擁有者。
    create_test_user(**test_admin_user_data)
    owner = create_test_user(**test_user_data)

    # 建立五筆訂單。
    for _ in range(5):
        create_test_order(owner.id, status="pending")
    test_db.commit()

    # 管理員透過 Session 登入。
    client = session_auth_client(test_admin_user_data)

    # 每頁只取兩筆，查詢第二頁。
    response = client.get(
        "/admin/orders/",
        params={"page": 2, "page_size": 2},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 5
    assert data["page"] == 2
    assert data["page_size"] == 2
    assert len(data["items"]) == 2


@pytest.mark.parametrize(
    "params",
    [
        {"page": 0},
        {"page": -1},
        {"page_size": 0},
        {"page_size": 101},
    ],
)
def test_admin_rejects_invalid_pagination(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    params,
):
    # 建立管理員並透過 Session 登入。
    create_test_user(**test_admin_user_data)
    client = session_auth_client(test_admin_user_data)

    response = client.get("/admin/orders/", params=params)

    # page 必須 >= 1，page_size 必須介於 1 到 100。
    assert response.status_code == 422


def test_admin_gets_empty_items_for_page_beyond_last(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
    create_test_order,
):
    # 建立管理員與訂單擁有者。
    create_test_user(**test_admin_user_data)
    owner = create_test_user(**test_user_data)

    # 建立三筆訂單。
    for _ in range(3):
        create_test_order(owner.id, status="pending")
    test_db.commit()

    client = session_auth_client(test_admin_user_data)

    # 每頁兩筆，共兩頁；查詢第三頁。
    response = client.get(
        "/admin/orders/",
        params={"page": 3, "page_size": 2},
    )

    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 3
    assert data["page"] == 3
    assert data["page_size"] == 2
    assert data["items"] == []


def test_admin_orders_are_sorted_by_id(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
    create_test_order,
):
    create_test_user(**test_admin_user_data)
    owner = create_test_user(**test_user_data)

    # 建立三筆訂單。
    for _ in range(3):
        create_test_order(owner.id, status="pending")
    test_db.commit()

    client = session_auth_client(test_admin_user_data)
    response = client.get("/admin/orders/")

    assert response.status_code == 200

    ids = [item["id"] for item in response.json()["items"]]
    assert ids == sorted(ids)


def test_admin_order_pages_have_no_duplicate_ids(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
    create_test_order,
):
    create_test_user(**test_admin_user_data)
    owner = create_test_user(**test_user_data)

    for _ in range(4):
        create_test_order(owner.id, status="pending")
    test_db.commit()

    client = session_auth_client(test_admin_user_data)

    page1 = client.get(
        "/admin/orders/",
        params={"page": 1, "page_size": 2},
    )
    page2 = client.get(
        "/admin/orders/",
        params={"page": 2, "page_size": 2},
    )

    assert page1.status_code == 200
    assert page2.status_code == 200

    ids1 = {item["id"] for item in page1.json()["items"]}
    ids2 = {item["id"] for item in page2.json()["items"]}

    assert len(ids1) == 2
    assert len(ids2) == 2
    assert ids1.isdisjoint(ids2)


def test_admin_rejects_invalid_order_status_filter(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
):
    create_test_user(**test_admin_user_data)
    client = session_auth_client(test_admin_user_data)

    response = client.get(
        "/admin/orders/",
        params={"status": "unknown"},
    )

    assert response.status_code == 422


def test_unauthenticated_user_cannot_list_admin_orders(test_client):
    response = test_client.get("/admin/orders/")

    assert response.status_code == 401


def test_admin_can_cancel_pending_order(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
    create_test_order,
):
    create_test_user(**test_admin_user_data)
    owner = create_test_user(**test_user_data)

    order = create_test_order(owner.id, status="pending")

    client = session_auth_client(test_admin_user_data)

    response = client.patch(
        f"/admin/orders/{order.id}/status",
        params={"new_status": "cancelled"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_admin_can_complete_processing_order(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
    create_test_order,
):
    create_test_user(**test_admin_user_data)
    owner = create_test_user(**test_user_data)

    order = create_test_order(owner.id, status="processing")

    client = session_auth_client(test_admin_user_data)

    response = client.patch(
        f"/admin/orders/{order.id}/status",
        params={"new_status": "completed"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_admin_cannot_change_completed_order_status(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
    create_test_order,
):
    create_test_user(**test_admin_user_data)
    owner = create_test_user(**test_user_data)

    order = create_test_order(owner.id, status="completed")

    client = session_auth_client(test_admin_user_data)

    response = client.patch(
        f"/admin/orders/{order.id}/status",
        params={"new_status": "processing"},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Cannot change order status from completed to processing"
    )


def test_unauthenticated_user_cannot_update_order_status(test_client):
    response = test_client.patch(
        "/admin/orders/999999/status",
        params={"new_status": "processing"},
    )

    assert response.status_code == 401


def test_unauthenticated_user_cannot_delete_order(test_client):
    response = test_client.delete("/admin/orders/999999")

    assert response.status_code == 401
