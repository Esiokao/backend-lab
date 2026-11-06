import os

import pytest
import requests

# 部署後的 smoke test：需要 CD workflow 注入的 DEPLOY_BASE_URL。
# 本機沒有這個變數 → 自動跳過（黃色），不再出現 KeyError 紅字；
# CD 部署後有變數 → 條件不成立，測試照常執行把關。
pytestmark = pytest.mark.skipif(
    "DEPLOY_BASE_URL" not in os.environ,
    reason="deployment-only tests: 需要 DEPLOY_BASE_URL（僅 CD workflow 提供）",
)


@pytest.mark.deployment
def test_health():
    base_url = os.environ["DEPLOY_BASE_URL"]

    response = requests.get(
        f"{base_url}/health",
        verify=False,
        timeout=10,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.deployment
def test_ready():
    base_url = os.environ["DEPLOY_BASE_URL"]

    response = requests.get(
        f"{base_url}/ready",
        verify=False,
        timeout=10,
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.deployment
def test_home_serves_html():
    """首頁應由 frontend image 服務出 HTML（edge nginx → frontend）。"""
    base_url = os.environ["DEPLOY_BASE_URL"]

    response = requests.get(
        base_url,
        verify=False,
        timeout=10,
    )

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


@pytest.mark.deployment
def test_login_reaches_redis():
    """Redis 探針：故意錯密碼的登入應回 401（或 429 限流）。

    /login 會先過 rate limit（Redis Lua eval）——Redis 壞掉時這條
    會 500 而不是 401，deployment smoke 就能抓到「API 活著但
    Redis 死了」的半殘狀態（staging 實錄）。
    """
    base_url = os.environ["DEPLOY_BASE_URL"]

    response = requests.post(
        f"{base_url}/api/login",
        json={"email": "smoke-probe@example.com", "password": "wrong-password-123"},
        verify=False,
        timeout=10,
    )

    assert response.status_code in (401, 429), (
        f"expected 401/429, got {response.status_code} — Redis pipeline may be broken"
    )
