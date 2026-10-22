from decimal import Decimal

from sqlalchemy import select

from app.core.events import PRODUCT_RESTOCKED
from app.models import Notification, NotificationOutbox, Product, ProductFollow
from app.workers.notifications import notify_product_restocked


def test_guest_can_list_products(test_client, test_db):
    test_db.add_all(
        [
            Product(
                name="Coffee Beans",
                description="Medium roast",
                price=Decimal("19.99"),
                stock=10,
            ),
            Product(
                name="Tea",
                description="Green tea",
                price=Decimal("9.99"),
                stock=5,
            ),
        ]
    )
    test_db.commit()

    response = test_client.get("/products/")

    assert response.status_code == 200

    body = response.json()
    assert len(body) == 2
    assert body[0]["name"] == "Coffee Beans"
    assert body[1]["name"] == "Tea"


def test_guest_can_get_product_detail(test_client, test_db):
    product = Product(
        name="Coffee Beans",
        description="Medium roast",
        price=Decimal("19.99"),
        stock=10,
    )
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)

    response = test_client.get(f"/products/{product.id}")

    assert response.status_code == 200
    assert response.json()["id"] == product.id
    assert response.json()["name"] == "Coffee Beans"
    assert response.json()["price"] == "19.99"


def test_get_missing_product_returns_404(test_client):
    response = test_client.get("/products/999999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_guest_can_search_products_by_name(test_client, test_db):
    test_db.add_all(
        [
            Product(
                name="Coffee Beans",
                price=Decimal("19.99"),
                stock=10,
            ),
            Product(
                name="Tea",
                price=Decimal("9.99"),
                stock=5,
            ),
        ]
    )
    test_db.commit()

    response = test_client.get(
        "/products/",
        params={"q": "coffee"},
    )

    assert response.status_code == 200

    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Coffee Beans"


def test_admin_can_create_product(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    admin_data = {**test_user_data, "role": "admin"}
    create_test_user(**admin_data)

    auth_client = session_auth_client(admin_data)

    response = auth_client.post(
        "/products/",
        json={
            "name": "Coffee Beans",
            "description": "Medium roast",
            "price": "19.99",
            "stock": 10,
        },
    )

    assert response.status_code == 201

    body = response.json()
    assert body["name"] == "Coffee Beans"
    assert body["price"] == "19.99"
    assert body["stock"] == 10


def test_regular_user_cannot_create_product(
    create_test_user,
    test_user_data,
    session_auth_client,
):
    create_test_user(**test_user_data)

    auth_client = session_auth_client(test_user_data)

    response = auth_client.post(
        "/products/",
        json={
            "name": "Coffee Beans",
            "price": "19.99",
            "stock": 10,
        },
    )

    assert response.status_code == 403


def test_create_product_rejects_negative_price_or_stock(
    create_test_user,
    test_user_data,
    session_auth_client,
):
    admin_data = {**test_user_data, "role": "admin"}
    create_test_user(**admin_data)

    auth_client = session_auth_client(admin_data)

    response = auth_client.post(
        "/products/",
        json={
            "name": "Invalid Product",
            "price": "-1.00",
            "stock": -5,
        },
    )

    assert response.status_code == 422


def test_admin_can_update_product(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    admin_data = {**test_user_data, "role": "admin"}
    create_test_user(**admin_data)

    product = Product(
        name="Old Name",
        price=Decimal("10.00"),
        stock=5,
    )
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)

    auth_client = session_auth_client(admin_data)

    response = auth_client.patch(
        f"/products/{product.id}",
        json={"name": "New Name"},
    )

    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["stock"] == 5


def test_restock_creates_outbox_event(
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
    )
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)

    auth_client = session_auth_client(admin_data)

    response = auth_client.patch(
        f"/products/{product.id}",
        json={"stock": 10},
    )

    assert response.status_code == 200

    event = (
        test_db.query(NotificationOutbox)
        .filter_by(
            event_type=PRODUCT_RESTOCKED,
        )
        .one()
    )

    assert event.payload == {"product_id": product.id}
    assert event.status == "pending"


def test_stock_increase_without_restock_does_not_create_event(
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
        stock=5,
    )
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)

    auth_client = session_auth_client(admin_data)

    response = auth_client.patch(
        f"/products/{product.id}",
        json={"stock": 10},
    )

    assert response.status_code == 200

    event_count = (
        test_db.query(NotificationOutbox)
        .filter_by(
            event_type=PRODUCT_RESTOCKED,
        )
        .count()
    )

    assert event_count == 0


def test_restock_worker_notifies_all_followers(
    test_db,
    create_test_user,
    test_user_data,
    create_test_order,
    create_test_outbox_event,
    worker_session_factory,
):
    user_a = create_test_user(**test_user_data)

    user_b_data = {
        **test_user_data,
        "email": "user-b@example.com",
        "name": "User B",
    }
    user_b = create_test_user(**user_b_data)

    product = Product(
        name="Coffee Beans",
        price=Decimal("19.99"),
        stock=10,
    )
    test_db.add(product)
    test_db.flush()

    test_db.add_all(
        [
            ProductFollow(
                user_id=user_a.id,
                product_id=product.id,
            ),
            ProductFollow(
                user_id=user_b.id,
                product_id=product.id,
            ),
        ]
    )

    event = create_test_outbox_event(
        event_type=PRODUCT_RESTOCKED,
        payload={"product_id": product.id},
    )

    notify_product_restocked(
        {
            "product_id": product.id,
            "outbox_event_id": event.id,
        },
        session_factory=worker_session_factory,
    )

    notifications = test_db.scalars(
        select(Notification).where(
            Notification.source_event_id == event.id,
        )
    ).all()

    assert len(notifications) == 2
    assert {notification.user_id for notification in notifications} == {
        user_a.id,
        user_b.id,
    }


def test_user_can_follow_product(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    user = create_test_user(**test_user_data)

    product = Product(
        name="Coffee Beans",
        price=Decimal("19.99"),
        stock=10,
    )
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)

    auth_client = session_auth_client(test_user_data)

    response = auth_client.post(
        f"/products/{product.id}/follow",
    )

    assert response.status_code == 200
    assert response.json() == {"following": True}

    follow = test_db.scalar(
        select(ProductFollow).where(
            ProductFollow.user_id == user.id,
            ProductFollow.product_id == product.id,
        )
    )

    assert follow is not None


def test_following_same_product_twice_is_idempotent(
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
    )
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)

    auth_client = session_auth_client(test_user_data)

    first_response = auth_client.post(
        f"/products/{product.id}/follow",
    )
    second_response = auth_client.post(
        f"/products/{product.id}/follow",
    )

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert second_response.json() == {"following": True}


def test_user_can_unfollow_product(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    user = create_test_user(**test_user_data)

    product = Product(
        name="Coffee Beans",
        price=Decimal("19.99"),
        stock=10,
    )
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)

    auth_client = session_auth_client(test_user_data)

    auth_client.post(f"/products/{product.id}/follow")

    response = auth_client.delete(
        f"/products/{product.id}/follow",
    )

    assert response.status_code == 200
    assert response.json() == {"following": False}

    follow = test_db.scalar(
        select(ProductFollow).where(
            ProductFollow.user_id == user.id,
            ProductFollow.product_id == product.id,
        )
    )

    assert follow is None


def test_admin_can_delete_product(
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
    )
    test_db.add(product)
    test_db.flush()

    auth_client = session_auth_client(admin_data)

    response = auth_client.delete(
        f"/products/{product.id}",
    )

    assert response.status_code == 204
    assert test_db.get(Product, product.id) is None


def test_admin_cannot_delete_product_referenced_by_order(
    test_db,
    create_test_user,
    test_user_data,
    create_test_order,
    session_auth_client,
):
    admin_data = {**test_user_data, "role": "admin"}
    user = create_test_user(**admin_data)

    product = Product(
        name="Coffee Beans",
        price=Decimal("19.99"),
        stock=10,
    )
    test_db.add(product)
    test_db.flush()

    order = create_test_order(user_id=user.id)
    order.product_id = product.id
    test_db.flush()

    auth_client = session_auth_client(admin_data)

    response = auth_client.delete(
        f"/products/{product.id}",
    )

    assert response.status_code == 409
    assert response.json()["detail"] == ("Product is referenced by existing orders")
    test_db.expire_all()
    assert test_db.get(Product, product.id) is not None
