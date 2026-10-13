# tests/auth/integration/test_session_auth.py

import pytest
from fastapi.testclient import TestClient

from app.core.redis import redis_client
from app.core.session import (
    COOKIE_NAME,
    SESSION_TTL_SECONDS,
    create_session,
    delete_session,
    get_session_user_id,
    revoke_all_user_sessions,
    user_sessions_key,
)
from app.main import app


@pytest.fixture(autouse=True)
def http_test_environment(monkeypatch):
    # TestClient 走 http://testserver；httpx 的 cookiejar
    # 不會送 Secure cookie，所以測試環境關閉 Secure flag。
    monkeypatch.setenv("COOKIE_SECURE", "false")


def _login(test_client, email, password="testpassword"):
    return test_client.post(
        "/login",
        json={"email": email, "password": password},
    )


def test_login_sets_session_cookie(test_client, create_test_user):
    create_test_user(email="cookie@example.com", password="testpassword")

    response = _login(test_client, "cookie@example.com")

    assert response.status_code == 200

    set_cookie = response.headers["set-cookie"]

    # HttpOnly：JS 讀不到；SameSite=strict：擋 CSRF；Path=/：全站有效。
    assert f"{COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=strict" in set_cookie
    assert "Path=/" in set_cookie
    # 測試環境（http）不該出現 Secure flag。
    assert "Secure" not in set_cookie


def test_cookie_session_authenticates(test_client, create_test_user):
    create_test_user(email="cookieauth@example.com", password="testpassword")

    login = _login(test_client, "cookieauth@example.com")

    assert login.status_code == 200

    # 不帶 Authorization header，只靠瀏覽器自動帶的 cookie。
    # /users/me 掛著 get_current_user，是標準的驗證探測點。
    response = test_client.get("/users/me")

    assert response.status_code == 200
    assert response.json()["email"] == "cookieauth@example.com"


def test_logout_invalidates_session(test_client, create_test_user):
    create_test_user(email="logout@example.com", password="testpassword")

    _login(test_client, "logout@example.com")

    # 登入後有 session cookie，可以存取。
    assert test_client.get("/users/me").status_code == 200

    sid = test_client.cookies.get(COOKIE_NAME)

    logout = test_client.post("/logout")

    assert logout.status_code == 200

    # Redis session 已刪除：sid 立即失效（真登出）。
    assert get_session_user_id(sid) is None

    # 之後的請求回到未登入狀態。
    assert test_client.get("/users/me").status_code == 401


def test_unauthenticated_request_rejected(test_client):
    # 沒有 cookie 也沒有 Bearer。
    response = test_client.get("/users/me")

    assert response.status_code == 401


def test_bearer_token_still_accepted(test_client, create_test_user):
    # 過渡期：非瀏覽器客戶端的 Bearer 路徑保持相容。
    # test_client fixture 已在 app 層級啟用 override_get_db（測試 DB），
    # 之後建立的新 TestClient 也會打到測試 DB。
    # 用全新的 client（沒有 cookie），證明走的是 Bearer 路徑。
    create_test_user(email="bearer@example.com", password="testpassword")

    login_client = TestClient(app)

    login = login_client.post(
        "/login",
        json={"email": "bearer@example.com", "password": "testpassword"},
    )

    token = login.json()["access_token"]

    fresh_client = TestClient(app)  # 沒有任何 cookie

    response = fresh_client.get(
        "/users/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200


def test_session_sliding_expiration():
    # 直接操作 session store，驗證滑動續期。
    sid = create_session(9999)
    key = f"session:{sid}"

    try:
        # 手動把 TTL 壓到 60 秒，模擬即將過期。
        redis_client.expire(key, 60)

        user_id = get_session_user_id(sid)

        assert user_id == 9999

        # 滑動續期：TTL 應該被拉回接近完整有效期。
        ttl = redis_client.ttl(key)

        assert ttl > SESSION_TTL_SECONDS - 60
    finally:
        delete_session(sid)


def test_password_change_revokes_all_sessions(test_client, create_test_user):
    # 改密碼前先登入，舊 session 可以存取。
    user = create_test_user(email="pwdchange@example.com", password="testpassword")

    login = _login(test_client, "pwdchange@example.com")

    assert login.status_code == 200
    assert test_client.get("/users/me").status_code == 200

    old_sid = test_client.cookies.get(COOKIE_NAME)

    # 再開第二個 session，模擬多裝置登入。
    second_sid = create_session(user.id)

    # 改密碼。
    patched = test_client.patch(
        f"/users/{user.id}",
        json={"password": "newpassword123"},
    )

    assert patched.status_code == 200

    # 兩個舊 session 都立即失效。
    assert get_session_user_id(old_sid) is None
    assert get_session_user_id(second_sid) is None
    assert test_client.get("/users/me").status_code == 401

    # 用新密碼可重新登入並正常存取。
    relogin = _login(test_client, "pwdchange@example.com", password="newpassword123")

    assert relogin.status_code == 200
    assert test_client.get("/users/me").status_code == 200

    # 登出路徑仍然正常：登出後變 401。
    assert test_client.post("/logout").status_code == 200
    assert test_client.get("/users/me").status_code == 401


def test_patch_without_password_keeps_session(test_client, create_test_user):
    # 只改 name 不該踢掉 session。
    user = create_test_user(email="keepalive@example.com", password="testpassword")

    _login(test_client, "keepalive@example.com")

    patched = test_client.patch(
        f"/users/{user.id}",
        json={"name": "NewName"},
    )

    assert patched.status_code == 200
    assert test_client.get("/users/me").status_code == 200


def test_session_index_ttl_slides_with_session():
    # 索引 TTL 也要跟著 session 一起滑動續期，否則活躍 session 會躲過撤銷。
    sid = create_session(9999)
    key = f"session:{sid}"
    index_key = user_sessions_key(9999)

    try:
        # 把索引 TTL 壓到 60 秒，模擬建立已久但持續活躍的使用者。
        redis_client.expire(index_key, 60)

        user_id = get_session_user_id(sid)

        assert user_id == 9999

        # 索引與 session 的 TTL 都該被拉回接近完整有效期。
        assert redis_client.ttl(index_key) > SESSION_TTL_SECONDS - 60
        assert redis_client.ttl(key) > SESSION_TTL_SECONDS - 60

        # 撤銷仍然找得到該 session。
        revoke_all_user_sessions(9999)

        assert get_session_user_id(sid) is None
    finally:
        delete_session(sid)
