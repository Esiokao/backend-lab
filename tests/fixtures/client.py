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
def session_auth_client(override_get_db):
    # 建立只使用 Session cookie 的登入測試 client。
    # 依賴 override_get_db：確保 app 的 get_db 已被換成測試交易
    # （原本這個副作用藏在 test_client 的依賴鏈裡，拆掉共享後必須自己拉）。
    # 每次呼叫回傳一個全新的 TestClient：session cookie 各自獨立，
    # 同一個測試登入多個角色（owner vs admin）不會互相覆蓋。
    def _session_auth_client(test_user_data):
        client = TestClient(app)

        response = client.post(
            "/login",
            json={
                "email": test_user_data["email"],
                "password": test_user_data["password"],
            },
        )

        assert response.status_code == 200

        # 確認登入成功後，伺服器有設定 Session cookie。
        assert response.cookies

        return client

    return _session_auth_client
