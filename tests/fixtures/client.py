# Test Client
import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def test_client(override_get_db):
    # 建立 FastAPI TestClient。
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_client(test_client):
    # 建立登入後的 TestClient。
    def _auth_client(test_user_data):
        response = test_client.post(
            "/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"],
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


@pytest.fixture
def session_auth_client(test_client):
    # 建立只使用 Session cookie 的登入測試 client。
    def _session_auth_client(test_user_data):
        response = test_client.post(
            "/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )

        assert response.status_code == 200

        # 確認登入成功後，伺服器有設定 Session cookie。
        assert response.cookies

        # 清除 JWT header，避免測試意外使用 JWT 通過驗證。
        test_client.headers.pop("Authorization", None)

        return test_client

    return _session_auth_client
