# tests/auth/integration/test_login.py

from app.core.jwt import decode_access_token


def test_login_success(test_client, create_test_user):
    # 建立測試使用者。
    test_user = create_test_user(
        email="login@example.com",
        password="testpassword",
    )

    # 使用正確的帳號密碼登入。
    response = test_client.post(
        "/login",
        json={
            "email": "login@example.com",
            "password": "testpassword",
        },
    )

    # 成功登入應該回傳 200。
    assert response.status_code == 200

    # 取得 response body。
    data = response.json()

    # 應該取得 Access Token。
    assert "access_token" in data

    # Token type 應該是 bearer。
    assert data["token_type"] == "bearer"

    token_data = decode_access_token(data["access_token"])

    assert token_data.sub == str(test_user.id)

    assert token_data.exp > 0


def test_login_wrong_password(test_client, create_test_user):
    # 建立測試使用者。
    create_test_user(
        email="login@example.com",
        password="testpassword",
    )

    # 使用錯誤密碼登入。
    response = test_client.post(
        "/login",
        json={
            "email": "login@example.com",
            "password": "wrongpassword",
        },
    )

    # 密碼錯誤應該回傳 401。
    assert response.status_code == 401

    # 確認錯誤訊息。
    assert response.json()["detail"] == "Invalid email or password"


def test_login_nonexistent_email(test_client, create_test_user):
    # create a use
    create_test_user(email="test@example.com", password="testpassword")

    # login with nonexistent email
    response = test_client.post(
        "/login",
        json={
            "email": "nonexistent@example.com",
            "password": "testpassword",
        },
    )

    # nonexistent email should return 401
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password"


def test_login_with_missing_email(test_client):
    response = test_client.post(
        "/login",
        json={
            "password": "testpassword",
        },
    )

    # missing email should return 422
    assert response.status_code == 422


def test_login_with_missing_password(test_client):
    # 不提供 password。
    response = test_client.post(
        "/login",
        json={
            "email": "test@example.com",
        },
    )

    # Missing password should return 422。
    assert response.status_code == 422


# 測試 /login 使用無效 email 格式。
def test_login_with_invalid_email(test_client):
    response = test_client.post(
        "/login",
        json={
            "email": "not-an-email",
            "password": "testpassword",
        },
    )

    # Invalid email format should return 422。
    assert response.status_code == 422


# 測試 /login password 太短。
def test_login_with_short_password(test_client):
    response = test_client.post(
        "/login",
        json={
            "email": "test@example.com",
            "password": "short",
        },
    )

    # Password shorter than 8 characters should return 422。
    assert response.status_code == 422


# 測試 /login password 太長。
def test_login_with_long_password(test_client):
    response = test_client.post(
        "/login",
        json={
            "email": "test@example.com",
            "password": "a" * 129,
        },
    )

    # Password longer than 128 characters should return 422。
    assert response.status_code == 422


def test_login_rate_limit(clear_rate_limit, test_client, create_test_user):
    # 建立測試使用者。
    create_test_user(
        email="login@example.com",
        password="testpassword",
    )

    # 前 5 次應該允許通過 rate limit。
    for _ in range(5):
        response = test_client.post(
            "/login",
            json={
                "email": "login@example.com",
                "password": "testpassword",
            },
        )

    assert response.status_code == 200

    # 第 6 次應該被 rate limit 擋下。
    response = test_client.post(
        "/login",
        json={
            "email": "login@example.com",
            "password": "testpassword",
        },
    )

    assert response.status_code == 429
    assert response.json()["detail"] == "Too many requests"
