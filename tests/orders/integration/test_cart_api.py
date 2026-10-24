from decimal import Decimal


def test_user_can_manage_cart_and_checkout(
    test_db,
    create_test_user,
    create_test_product,
    test_user_data,
    session_auth_client,
):
    create_test_user(**test_user_data)
    product = create_test_product(name="Beans", price=Decimal("10.00"), stock=5)
    test_db.commit()
    client = session_auth_client(test_user_data)

    response = client.post(
        "/cart/items", json={"product_id": product.id, "quantity": 2}
    )
    assert response.status_code == 201
    assert response.json()["items"][0]["quantity"] == 2

    response = client.patch(f"/cart/items/{product.id}", json={"quantity": 3})
    assert response.status_code == 200
    assert response.json()["total"] == "30.00"

    response = client.delete(f"/cart/items/{product.id}")
    assert response.status_code == 200
    assert response.json()["items"] == []

    client.post("/cart/items", json={"product_id": product.id, "quantity": 2})
    response = client.post("/cart/checkout")
    assert response.status_code == 200
    assert response.json()["items"][0]["quantity"] == 2

    response = client.get("/cart")
    assert response.status_code == 200
    assert response.json()["items"] == []
    test_db.refresh(product)
    assert product.stock == 3


def test_cart_is_private_and_clearable(
    create_test_user,
    create_test_product,
    test_user_data,
    session_auth_client,
):
    create_test_user(**test_user_data)
    product = create_test_product()
    client = session_auth_client(test_user_data)
    client.post("/cart/items", json={"product_id": product.id, "quantity": 1})

    response = client.delete("/cart")
    assert response.status_code == 200
    assert response.json() == {"items": [], "total": "0"}


def test_add_product_to_cart_and_view_cart(
    create_test_user, create_test_product, test_user_data, session_auth_client
):
    create_test_user(**test_user_data)
    product = create_test_product(name="Beans")
    client = session_auth_client(test_user_data)

    response = client.post(
        "/cart/items", json={"product_id": product.id, "quantity": 2}
    )
    assert response.status_code == 201

    response = client.get("/cart")
    assert response.status_code == 200
    assert response.json()["items"][0]["product_id"] == product.id
    assert response.json()["items"][0]["quantity"] == 2


def test_update_cart_quantity(
    create_test_user, create_test_product, test_user_data, session_auth_client
):
    create_test_user(**test_user_data)
    product = create_test_product()
    client = session_auth_client(test_user_data)
    client.post("/cart/items", json={"product_id": product.id, "quantity": 1})

    response = client.patch(f"/cart/items/{product.id}", json={"quantity": 4})
    assert response.status_code == 200
    assert response.json()["items"][0]["quantity"] == 4


def test_remove_cart_item(
    create_test_user, create_test_product, test_user_data, session_auth_client
):
    create_test_user(**test_user_data)
    product = create_test_product()
    client = session_auth_client(test_user_data)
    client.post("/cart/items", json={"product_id": product.id, "quantity": 1})

    response = client.delete(f"/cart/items/{product.id}")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_empty_cart_cannot_checkout(
    create_test_user, test_user_data, session_auth_client
):
    create_test_user(**test_user_data)
    response = session_auth_client(test_user_data).post("/cart/checkout")
    assert response.status_code == 400
    assert response.json()["detail"] == "Cart is empty"


def test_cannot_add_missing_or_inactive_product(
    test_db, create_test_user, create_test_product, test_user_data, session_auth_client
):
    create_test_user(**test_user_data)
    inactive = create_test_product(is_active=False)
    client = session_auth_client(test_user_data)

    response = client.post("/cart/items", json={"product_id": 999999, "quantity": 1})
    assert response.status_code == 404

    response = client.post(
        "/cart/items", json={"product_id": inactive.id, "quantity": 1}
    )
    assert response.status_code == 404


def test_cart_is_private_between_users(
    create_test_user,
    create_test_product,
    test_user_data,
    test_random_user_data,
    session_auth_client,
):
    create_test_user(**test_user_data)
    create_test_user(**test_random_user_data)
    product = create_test_product()
    session_auth_client(test_user_data).post(
        "/cart/items", json={"product_id": product.id, "quantity": 2}
    )

    response = session_auth_client(test_random_user_data).get("/cart")
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_guest_cannot_use_cart(test_client):
    response = test_client.get("/cart")
    assert response.status_code == 401
