from unittest.mock import AsyncMock, patch

import pytest
from fastapi import HTTPException, Request, Response
from starlette.requests import Request as StarletteRequest

from app.core.request_size import (
    RequestSizeChecker,
    RequestSizeRoute,
    create_request_size_checker,
)


@pytest.mark.asyncio
async def test_mock_receive():
    # 建立 mock receive，模擬 ASGI async receive()。
    mock_receive = AsyncMock()

    # 模擬 request body 分成兩個 chunk。
    mock_receive.side_effect = [
        {
            "type": "http.request",
            "body": b"x" * (600 * 1024),
            "more_body": True,
        },
        {
            "type": "http.request",
            "body": b"y" * (600 * 1024),
            "more_body": False,
        },
    ]

    # 建立假的 HTTP request scope。
    mock_scope = {
        "type": "http",
        "method": "POST",
        "path": "/test",
        "headers": [],
    }

    # 建立 Starlette Request。
    request = StarletteRequest(
        scope=mock_scope,
        receive=mock_receive,
    )

    # 第一次呼叫 receive()。
    message1 = await request.receive()
    message2 = await request.receive()

    # 確認第一次拿到 600 KB。
    assert len(message1["body"]) == 600 * 1024
    assert len(message2["body"]) == 600 * 1024
    assert message1["body"] == b"x" * (600 * 1024)
    assert message2["body"] == b"y" * (600 * 1024)


@pytest.mark.asyncio
async def test_request_size_rejects_oversized_streaming_body():
    # 模擬 ASGI receive()。
    receive = AsyncMock()

    # 模擬 request body 分成兩個 chunk。
    # 600 KB + 600 KB = 1.2 MB > 1 MB limit。
    receive.side_effect = [
        {
            "type": "http.request",
            "body": b"x" * (600 * 1024),
            "more_body": True,
        },
        {
            "type": "http.request",
            "body": b"y" * (600 * 1024),
            "more_body": False,
        },
    ]

    # 建立假的 HTTP scope。
    scope = {
        "type": "http",
        "method": "POST",
        "path": "/test",
        "headers": [],
    }

    # 建立真的 Starlette Request。
    # 但 receive 是我們控制的 AsyncMock。
    request = StarletteRequest(
        scope=scope,
        receive=receive,
    )

    # 模擬 FastAPI 原本的 route handler。
    #
    # 我們不想測 FastAPI handler 本身，
    # 但它必須讀取 request body，
    # 才能觸發 RequestSizeRoute 的 limited_receive()。
    async def mock_original_handler(request: Request):
        await request.body()
        return Response(status_code=200)

    # 建立真正的 RequestSizeRoute。
    route = RequestSizeRoute(
        path="/test",
        endpoint=lambda request: None,
        methods=["POST"],
    )

    # RequestSizeRoute.get_route_handler()
    # 內部會呼叫 FastAPI 的 get_request_handler()
    # 來建立 original_route_handler。
    #
    # 我們把這一層替換成自己的 mock handler。
    with patch(
        "fastapi.routing.get_request_handler",
        return_value=mock_original_handler,
    ):
        # 這裡取得的是 RequestSizeRoute 包裝後的 handler。
        handler = route.get_route_handler()

        # 執行真正的 RequestSizeRoute logic。
        with pytest.raises(HTTPException) as exc_info:
            await handler(request)

    # 確認是 Request Entity Too Large。
    assert exc_info.value.status_code == 413


def test_request_size_checker_accepts_body_within_limit():
    # 建立 1 MB request size limit。
    checker = RequestSizeChecker(1024 * 1024)

    # 收到 600 KB。
    checker.add(600 * 1024)

    # 目前沒有超過限制。
    assert checker.total_received == 600 * 1024


def test_request_size_checker_rejects_oversized_body():
    # 建立 1 MB request size limit。
    checker = RequestSizeChecker(1024 * 1024)

    # 第一個 chunk：600 KB。
    checker.add(600 * 1024)

    # 第二個 chunk：600 KB，總共 1.2 MB。
    with pytest.raises(HTTPException) as exc_info:
        checker.add(600 * 1024)

    assert exc_info.value.status_code == 413
    assert checker.total_received == 1200 * 1024


def test_create_request_size_checker():
    # Factory 應該建立 RequestSizeChecker。
    checker = create_request_size_checker(1024)

    assert isinstance(checker, RequestSizeChecker)
    assert checker.max_size == 1024
    assert checker.total_received == 0
