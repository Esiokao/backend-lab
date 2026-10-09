import os

import pytest
import requests


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
