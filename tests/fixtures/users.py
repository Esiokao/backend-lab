import uuid

import pytest

from app.core.security import hash_password
from app.models import User


@pytest.fixture
def create_test_user(test_db):
    # 建立 User 的 factory。
    def _create_user(
        name="TestUser",
        email=None,
        password="testpassword",
        role="user",
    ):
        if email is None:
            email = f"{uuid.uuid4()}@test.com"

        user = User(
            name=name,
            email=email,
            password_hash=hash_password(password),
            role=role,
        )

        test_db.add(user)
        test_db.flush()
        test_db.refresh(user)

        return user

    return _create_user


@pytest.fixture
def test_user_data():
    return {
        "name": "TestUser",
        "email": "test@example.com",
        "password": "testpassword",
        "role": "user",
    }


@pytest.fixture
def test_random_user_data():
    return {
        "name": "Random User",
        "email": f"{uuid.uuid4()}@test.com",
        "password": "randompassword",
        "role": "user",
    }


@pytest.fixture
def test_admin_user_data():
    return {
        "name": "AdminUser",
        "email": f"{uuid.uuid4()}@test.com",
        "password": "adminpassword",
        "role": "admin",
    }
