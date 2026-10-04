# tests/request/integration/conftest.py

import pytest
from fastapi import APIRouter, FastAPI, Request

from app.core.request_size import RequestSizeRoute


@pytest.fixture
def mock_app():
    # 建立測試專用 FastAPI app。
    app = FastAPI()

    # 使用真正的 RequestSizeRoute。
    router = APIRouter(route_class=RequestSizeRoute)

    @router.post("/test")
    async def endpoint_under_test(request: Request):
        # 讀取 request body，觸發 RequestSizeRoute 的 receive wrapper。
        await request.body()

        return {"ok": True}

    app.include_router(router)

    return app, router
