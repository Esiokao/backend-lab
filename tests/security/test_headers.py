import requests

BASE_URL = "https://localhost"


def test_security_headers():
    """Verify security headers returned by Nginx."""
    response = requests.get(
        BASE_URL,
        verify=False,
        timeout=5,
    )

    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert response.headers["Strict-Transport-Security"] == "max-age=31536000"
