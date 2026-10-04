# app/core/request_size.py

import os
from collections.abc import Callable

from dotenv import load_dotenv
from fastapi import HTTPException
from fastapi.routing import APIRoute
from starlette.requests import Request

load_dotenv()


# 沒有特別設定時，每個 request 預設最多 1 MB。
DEFAULT_MAX_REQUEST_SIZE = int(
    os.getenv(
        "DEFAULT_MAX_REQUEST_SIZE",
        str(1 * 1024 * 1024),
    )
)


# decorator
# 給 endpoint 掛上 metadata。
def request_size_limit(max_size: int):
    """設定單一 endpoint 的 request body 大小限制。"""

    if max_size <= 0:
        raise ValueError("max_size must be greater than 0")

    def decorator(func: Callable):
        # 給 endpoint 加上 metadata。
        func.max_request_size = max_size
        return func

    return decorator


# max request size getter
def get_request_size_limit(endpoint: Callable) -> int:
    """取得 endpoint 的限制，沒有設定就使用預設值。"""
    return getattr(
        endpoint,
        "max_request_size",
        DEFAULT_MAX_REQUEST_SIZE,
    )


class RequestSizeChecker:
    """追蹤 request body 大小，並檢查是否超過限制。"""

    def __init__(self, max_size: int):
        self.max_size = max_size
        self.total_received = 0

    def add(self, size: int) -> None:
        """累積收到的 bytes，超過限制時拋出 413。"""
        self.total_received += size

        if self.total_received > self.max_size:
            raise HTTPException(
                status_code=413,
                detail="Request body too large",
            )


# RequestSizeChecker 的 factory。
# 目前 factory 使用 RequestSizeChecker 作為 implementation。
def create_request_size_checker(max_size: int) -> RequestSizeChecker:
    """建立 request size checker。"""
    return RequestSizeChecker(max_size)


class RequestSizeRoute(APIRoute):
    """在 route 層執行 request size policy。"""

    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        max_size = get_request_size_limit(self.endpoint)

        async def custom_route_handler(request: Request):
            # 透過 factory 建立這個 request 專屬的 checker。
            checker = create_request_size_checker(max_size)

            content_length = request.headers.get("content-length")

            if content_length is not None:
                try:
                    if int(content_length) > max_size:
                        raise HTTPException(
                            status_code=413,
                            detail="Request body too large",
                        )
                except ValueError:
                    # Content-Length 格式錯誤時，不依賴這個 header。
                    pass

            # 新的reciever,
            # 用來多一層檢查, 但一樣return messsage
            async def limited_receive():
                original_receive = request.receive
                message = await original_receive()

                body = message.get("body", b"")

                # 每收到一個 chunk，就交給 checker 累積。
                checker.add(len(body))

                return message

            limited_request = Request(
                scope=request.scope,
                receive=limited_receive,
            )

            return await original_route_handler(limited_request)

        return custom_route_handler
