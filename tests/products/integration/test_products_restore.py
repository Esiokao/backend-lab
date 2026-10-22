from decimal import Decimal

from app.models import Product


def test_admin_can_restore_archived_product(
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
        stock=0,
        is_active=False,
    )
    test_db.add(product)
    test_db.flush()

    auth_client = session_auth_client(admin_data)

    response = auth_client.patch(
        f"/products/{product.id}/restore",
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is True

    test_db.refresh(product)
    assert product.is_active is True


def test_regular_user_cannot_restore_archived_product(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    create_test_user(**test_user_data)

    product = Product(
        name="Coffee Beans",
        price=Decimal("19.99"),
        stock=0,
        is_active=False,
    )
    test_db.add(product)
    test_db.flush()

    auth_client = session_auth_client(test_user_data)

    response = auth_client.patch(
        f"/products/{product.id}/restore",
    )

    assert response.status_code == 403

    test_db.refresh(product)
    assert product.is_active is False
