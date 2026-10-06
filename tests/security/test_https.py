import requests

BASE_URL = "http://localhost"


def test_http_redirects_to_https():
    """Verify HTTP requests are redirected to HTTPS."""
    response = requests.get(
        BASE_URL,
        allow_redirects=False,
        timeout=5,
    )

    assert response.status_code == 301
    assert response.headers["Location"].startswith("https://")
