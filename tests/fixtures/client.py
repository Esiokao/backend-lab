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
