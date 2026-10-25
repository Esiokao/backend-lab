# tests/orders/integration/test_order_price_snapshot.py
# 訂單價格快照不變量（issue #3）：order_items.unit_price 為下單當下的快照，
# 商品之後改價不影響歷史訂單；cart 則顯示 live price（結帳當下才定錨）。


def test_order_unit_price_is_snapshot_after_product_price_change(
    session_auth_client,
    create_test_user,
    test_user_data,
    create_test_product,
    create_test_order,
    test_admin_user_data,
):
    # Arrange：商品定價 32.00，建立訂單（快照 unit_price=32.00）。
    user = create_test_user(**test_user_data)
    create_test_user(**test_admin_user_data)
    product = create_test_product(price=32)
    order = create_test_order(user_id=user.id, product=product, quantity=2)
    owner_client = session_auth_client(test_user_data)
    admin_client = session_auth_client(test_admin_user_data)

    before = owner_client.get(f"/orders/{order.id}")
    assert before.status_code == 200
    assert before.json()["items"][0]["unit_price"] == "32.00"

    # Act：admin 把商品改價 32 → 99.99。
    patch = admin_client.patch(f"/products/{product.id}", json={"price": "99.99"})
    assert patch.status_code == 200

    # Assert：歷史訂單的快照價與明細不動。
    after = owner_client.get(f"/orders/{order.id}")
    assert after.status_code == 200
    item = after.json()["items"][0]
    assert item["unit_price"] == "32.00"
    assert item["quantity"] == 2
    assert item["product_id"] == product.id


def test_cart_shows_live_price_after_product_price_change(
    session_auth_client,
    create_test_user,
    test_user_data,
    create_test_product,
    test_admin_user_data,
):
    # Arrange：商品定價 32.00，使用者放一件進購物車。
    create_test_user(**test_admin_user_data)
    create_test_user(**test_user_data)
    product = create_test_product(price=32)
    client = session_auth_client(test_user_data)

    add = client.post("/cart/items", json={"product_id": product.id, "quantity": 1})
    assert add.status_code == 201
    assert add.json()["items"][0]["unit_price"] == "32.00"

    # Act：admin 改價 32 → 99.99。
    admin_client = session_auth_client(test_admin_user_data)
    patch = admin_client.patch(f"/products/{product.id}", json={"price": "99.99"})
    assert patch.status_code == 200

    # Assert：購物車顯示的是 live price（下單才快照）。
    cart = client.get("/cart")
    assert cart.status_code == 200
    assert cart.json()["items"][0]["unit_price"] == "99.99"
