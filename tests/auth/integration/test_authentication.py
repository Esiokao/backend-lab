# tests/auth/integration/test_authentication.py

from datetime import datetime, timedelta, timezone

import jwt
from fastapi.testclient import TestClient

from app.core.jwt import JWT_ALGORITHM, JWT_SECRET


def test_get_current_user_with_invalid_token(test_client: TestClient):
    # Fake token。
    fake_token = {"Authorization": "Bearer invalid_token"}
    test_client.headers.update(fake_token)

    # Attempt to access API requiring authentication。
    response = test_client.get("/users/me")

    # Invalid token should return 401。
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_get_current_user_without_token(test_client: TestClient):
    # 不提供 Authorization header。
    response = test_client.get("/users/me")

    # 沒有 token 應該被拒絕。
    assert response.status_code == 401


def test_get_current_user_with_expierd_token(test_client: TestClient):
    # Create an expired token by manually setting the expiration time。
    expired_time = datetime.now(timezone.utc) - timedelta(minutes=1)

    payload = {
        "sub": 1,
        "exp": expired_time,
    }

    token = jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    # Update Authorization header。
    test_client.headers.update({"Authorization": f"Bearer {token}"})

    # Attempt to access API requiring authentication。
    response = test_client.get("/users/me")

    # Expired token should return 401。
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_get_current_user_with_missing_sub(test_client: TestClient):
    # Create a JWT without "sub"。
    missing_sub_payload = {"exp": datetime.now(timezone.utc) + timedelta(minutes=1)}

    token = jwt.encode(
        missing_sub_payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    test_client.headers.update({"Authorization": f"Bearer {token}"})

    response = test_client.get("/users/me")

    # Missing sub should return 401。
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_get_current_user_with_nonexistent_user(test_client: TestClient):
    # Create a payload with a nonexistent user ID。
    payload = {
        "sub": 9999999999999999999999999999999999999999,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=1),
    }

    token = jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    # Update Authorization header。
    test_client.headers.update({"Authorization": f"Bearer {token}"})

    # Attempt to access API requiring authentication。
    response = test_client.get("/users/me")

    # Nonexistent user should return 401。
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid or expired token"}


def test_get_current_user_with_invalid_sub_type(
    test_client: TestClient,
):
    # 建立一個 sub 型別錯誤的 JWT。
    payload = {
        "sub": [],
        "exp": datetime.now(timezone.utc) + timedelta(minutes=1),
    }

    # 建立 JWT。
    token = jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    # 使用錯誤格式的 Token。
    test_client.headers.update({"Authorization": f"Bearer {token}"})

    response = test_client.get("/users/me")

    # sub 型別錯誤應該被拒絕。
    assert response.status_code == 401


def test_get_current_user_with_null_sub(test_client: TestClient):
    # 建立一個 sub 為 null 的 JWT。
    payload = {
        "sub": None,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=1),
    }

    # 建立 JWT。
    token = jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    # 使用 sub=null 的 Token。
    test_client.headers.update({"Authorization": f"Bearer {token}"})

    response = test_client.get("/users/me")

    # sub 為 null 應該被拒絕。
    assert response.status_code == 401


def test_get_current_user_with_empty_sub(test_client: TestClient):
    # 建立 sub 為空字串的 JWT。
    payload = {
        "sub": "",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=1),
    }

    # 建立 JWT。
    token = jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    # 使用 sub="" 的 Token。
    test_client.headers.update({"Authorization": f"Bearer {token}"})

    response = test_client.get("/users/me")

    # 空的 sub 應該被拒絕。
    assert response.status_code == 401
