# tests/conftest.py

import uuid

import pytest
from fastapi.testclient import TestClient

from app.core.redis import redis_client
from app.core.security import hash_password
from app.database import get_db
from app.main import app
from app.models import Order, User

# Load database fixtures.
from tests.fixtures.database import test_db


# Test Client
@pytest.fixture
def test_client(override_get_db):
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_client(test_client):
    def _auth_client(user_data):
        response = test_client.post(
            "/login",
            json={
                "email": user_data["email"],
                "password": user_data["password"],
            },
        )

        token = response.json()["access_token"]

        test_client.headers.update(
            {
                "Authorization": f"Bearer {token}",
            }
        )

        return test_client

    return _auth_client


# Redis Fixtures
@pytest.fixture(autouse=True)
def clear_rate_limit():
    # 測試開始前清除 rate limit keys。
    for key in redis_client.scan_iter(match="rate_limit:*"):
        redis_client.delete(key)

    yield

    # 測試結束後清除 rate limit keys。
    for key in redis_client.scan_iter(match="rate_limit:*"):
        redis_client.delete(key)


# Database Fixtures
@pytest.fixture
def override_get_db(test_db):
    # 測試時讓 FastAPI 使用 transaction session。
    def _override_get_db():
        yield test_db

    # 將正式 DB dependency 替換成測試 DB。
    app.dependency_overrides[get_db] = _override_get_db

    yield

    # 測試結束後移除 override。
    app.dependency_overrides.pop(get_db, None)


# Fixed User Data
@pytest.fixture
def test_user_data():
    # 提供固定的 User 測試資料。
    return {
        "name": "TestUser",
        "email": "test@example.com",
        "password": "testpassword",
    }


# Random User Data
@pytest.fixture
def test_random_user_data():
    return {
        "name": "Random User",
        "email": f"{uuid.uuid4()}@example.com",
        "password": "randompassword",
    }


@pytest.fixture
def test_user(test_db, test_user_data):
    db = test_db

    user = User(
        name=test_user_data["name"],
        email=test_user_data["email"],
        password_hash=hash_password(test_user_data["password"]),
    )

    db.add(user)
    db.flush()
    db.refresh(user)

    yield user


@pytest.fixture
def test_random_user(test_db, test_random_user_data):
    db = test_db

    user = User(
        name=test_random_user_data["name"],
        email=test_random_user_data["email"],
        password_hash=hash_password(test_random_user_data["password"]),
    )

    db.add(user)
    db.flush()
    db.refresh(user)

    yield user


@pytest.fixture
def test_other_order(test_db, test_random_user):
    db = test_db

    order = Order(
        user_id=test_random_user.id,
    )

    db.add(order)
    db.flush()
    db.refresh(order)

    yield order


@pytest.fixture
def test_order(test_db, test_user):
    db = test_db

    order = Order(
        user_id=test_user.id,
    )

    db.add(order)
    db.flush()
    db.refresh(order)

    yield order
