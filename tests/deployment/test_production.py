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
