# tests/orders/integration/test_cart_checkout_selection.py
# 勾選式結帳：POST /cart/checkout {product_ids} 只出選中商品，其餘留車。

from decimal import Decimal


def test_checkout_selected_items_only(
    test_db,
    create_test_user,
    create_test_product,
    test_user_data,
    session_auth_client,
):
    create_test_user(**test_user_data)
    beans = create_test_product(name="Beans", price=Decimal("10.00"), stock=5)
    corn = create_test_product(name="Corn", price=Decimal("4.00"), stock=5)
    test_db.commit()
    client = session_auth_client(test_user_data)

    client.post("/cart/items", json={"product_id": beans.id, "quantity": 2})
    client.post("/cart/items", json={"product_id": corn.id, "quantity": 1})

    response = client.post("/cart/checkout", json={"product_ids": [beans.id]})

    assert response.status_code == 200
    order = response.json()
    assert [item["quantity"] for item in order["items"]] == [2]

    # 未選中的 Corn 留在車上。
    response = client.get("/cart")
    assert [item["product_name"] for item in response.json()["items"]] == ["Corn"]

    test_db.refresh(beans)
    test_db.refresh(corn)
    assert beans.stock == 3
    assert corn.stock == 5


def test_checkout_without_body_takes_whole_cart(
    create_test_user,
    create_test_product,
    test_user_data,
    session_auth_client,
):
    create_test_user(**test_user_data)
    beans = create_test_product(name="Beans", price=Decimal("10.00"), stock=5)
    client = session_auth_client(test_user_data)
    client.post("/cart/items", json={"product_id": beans.id, "quantity": 1})

    response = client.post("/cart/checkout")

    assert response.status_code == 200
    assert len(response.json()["items"]) == 1


def test_cart_items_expose_current_stock(
    create_test_user,
    create_test_product,
    test_user_data,
    session_auth_client,
):
    # 新契約：加車當下就擋超庫存（422），回應仍帶 stock 供前端顯示「僅剩 N 件」。
    create_test_user(**test_user_data)
    beans = create_test_product(name="Beans", price=Decimal("10.00"), stock=2)
    client = session_auth_client(test_user_data)

    # 超庫存：5 > 2 → 422，訊息帶剩餘庫存。
    response = client.post("/cart/items", json={"product_id": beans.id, "quantity": 5})

    assert response.status_code == 422
    assert "2" in response.json()["detail"]

    # 合法加購：quantity == stock → 201，回應帶即時庫存。
    response = client.post("/cart/items", json={"product_id": beans.id, "quantity": 2})

    assert response.status_code == 201
    item = response.json()["items"][0]
    assert item["quantity"] == 2
    assert item["stock"] == 2  # 前端據此顯示庫存狀態
