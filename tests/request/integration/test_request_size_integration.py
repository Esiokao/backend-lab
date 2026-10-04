# tests/request/integration/test_request_size_integration.py

from fastapi import Request
from fastapi.testclient import TestClient

from app.core.request_size import request_size_limit


def test_api(mock_app):
    app, _ = mock_app
    client = TestClient(app)

    response = client.post(
        "/test",
        json={},
    )

    assert response.status_code == 200


def test_api_with_oversize(mock_app):
    app, _ = mock_app
    client = TestClient(app)

    response = client.post(
        "/test",
        content=b"x" * (1024 * 1024 + 1),
    )

    assert response.status_code == 413


def test_api_rejects_oversized_content_length(mock_app):
    app, _ = mock_app
    client = TestClient(app)

    response = client.post(
        "/test",
        headers={
            "content-length": str(1024 * 1024 + 1),
        },
        content=b"",
    )

    assert response.status_code == 413


def test_api_uses_endpoint_specific_limit(mock_app):
    app, router = mock_app

    @router.post("/limited")
    @request_size_limit(100 * 1024)
    async def limited_endpoint(request: Request):
        # 讀取 request body，觸發 RequestSizeRoute 的 receive wrapper。
        await request.body()

        return {"ok": True}

    client = TestClient(app)

    response = client.post(
        "/limited",
        content=b"x" * (101 * 1024),
    )

    assert response.status_code == 413


def test_api_ignores_invalid_content_length(mock_app):
    app, _ = mock_app
    client = TestClient(app)

    response = client.post(
        "/test",
        headers={
            "content-length": "invalid",
        },
        json={},
    )

    assert response.status_code == 200


def test_api_rejects_oversized_body_even_when_content_length_is_under_limit(
    mock_app,
):
    app, _ = mock_app
    client = TestClient(app)

    response = client.post(
        "/test",
        headers={
            # Content-Length 宣稱只有 500 KB。
            "content-length": str(500 * 1024),
        },
        # 實際 body 超過 1 MB。
        content=b"x" * (1024 * 1024 + 1),
    )

    assert response.status_code == 413
