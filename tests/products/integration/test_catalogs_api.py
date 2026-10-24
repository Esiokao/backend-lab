from decimal import Decimal

from app.models import Category, Product


def test_guest_can_list_and_get_catalogs(test_client, test_db):
    catalog = Category(name="Coffee", description="Coffee products")
    test_db.add(catalog)
    test_db.commit()
    test_db.refresh(catalog)

    response = test_client.get("/categories/")
    assert response.status_code == 200
    assert response.json()[0]["name"] == "Coffee"

    response = test_client.get(f"/categories/{catalog.id}")
    assert response.status_code == 200
    assert response.json()["description"] == "Coffee products"


def test_catalog_crud_requires_admin(
    create_test_user,
    test_user_data,
    session_auth_client,
):
    create_test_user(**test_user_data)
    client = session_auth_client(test_user_data)

    response = client.post("/categories/", json={"name": "Coffee"})
    assert response.status_code == 403


def test_admin_can_create_update_and_delete_catalog(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    admin_data = {**test_user_data, "role": "admin"}
    create_test_user(**admin_data)
    client = session_auth_client(admin_data)

    response = client.post(
        "/categories/", json={"name": "Coffee", "description": "Beans"}
    )
    assert response.status_code == 201
    catalog_id = response.json()["id"]

    response = client.patch(f"/categories/{catalog_id}", json={"name": "Tea"})
    assert response.status_code == 200
    assert response.json()["name"] == "Tea"

    product = Product(
        name="Tea product", price=Decimal("10.00"), stock=1, category_id=catalog_id
    )
    test_db.add(product)
    test_db.commit()

    response = client.delete(f"/categories/{catalog_id}")
    assert response.status_code == 204
    test_db.refresh(product)
    assert product.category_id is None


def test_product_catalog_create_update_and_filter(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    catalog = Category(name="Coffee")
    test_db.add(catalog)
    test_db.commit()
    test_db.refresh(catalog)

    admin_data = {**test_user_data, "role": "admin"}
    create_test_user(**admin_data)
    client = session_auth_client(admin_data)

    response = client.post(
        "/products/",
        json={
            "name": "Beans",
            "price": "19.99",
            "stock": 10,
            "category_id": catalog.id,
        },
    )
    assert response.status_code == 201
    product_id = response.json()["id"]
    assert response.json()["category_id"] == catalog.id

    response = client.patch(f"/products/{product_id}", json={"category_id": None})
    assert response.status_code == 200
    assert response.json()["category_id"] is None

    response = client.get("/products/", params={"category_id": catalog.id})
    assert response.status_code == 200
    assert response.json() == []
