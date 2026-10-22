from decimal import Decimal

from app.models import Product


def test_admin_can_list_archived_products(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    admin_data = {**test_user_data, "role": "admin"}
    create_test_user(**admin_data)

    active_product = Product(
        name="Active Product",
        price=Decimal("10.00"),
        stock=5,
        is_active=True,
    )

    archived_product = Product(
        name="Archived Product",
        price=Decimal("20.00"),
        stock=0,
        is_active=False,
    )

    test_db.add_all([active_product, archived_product])
    test_db.flush()

    auth_client = session_auth_client(admin_data)

    response = auth_client.get("/products/archived")

    assert response.status_code == 200

    items = response.json()
    assert len(items) == 1
    assert items[0]["name"] == "Archived Product"
    assert items[0]["is_active"] is False


def test_regular_user_cannot_list_archived_products(
    create_test_user,
    test_user_data,
    session_auth_client,
):
    create_test_user(**test_user_data)

    auth_client = session_auth_client(test_user_data)

    response = auth_client.get("/products/archived")

    assert response.status_code == 403


def test_admin_can_archive_product(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    admin_data = {**test_user_data, "role": "admin"}
    create_test_user(**admin_data)

    product = Product(
        name="Coffee Beans",
        price=Decimal("19.99"),
        stock=10,
        is_active=True,
    )
    test_db.add(product)
    test_db.flush()

    auth_client = session_auth_client(admin_data)

    response = auth_client.patch(
        f"/products/{product.id}/archive",
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    test_db.refresh(product)
    assert product.is_active is False


def test_regular_user_cannot_archive_product(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    create_test_user(**test_user_data)

    product = Product(
        name="Coffee Beans",
        price=Decimal("19.99"),
        stock=10,
        is_active=True,
    )
    test_db.add(product)
    test_db.flush()

    auth_client = session_auth_client(test_user_data)

    response = auth_client.patch(
        f"/products/{product.id}/archive",
    )

    assert response.status_code == 403


def test_archived_product_is_hidden_from_public_list(
    test_db,
    test_client,
):
    product = Product(
        name="Archived Product",
        price=Decimal("19.99"),
        stock=0,
        is_active=False,
    )
    test_db.add(product)
    test_db.flush()

    response = test_client.get("/products/")

    assert response.status_code == 200
    assert all(item["id"] != product.id for item in response.json())
