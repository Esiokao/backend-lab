# app/core/rate_limit.py

import os

from dotenv import load_dotenv
from fastapi import HTTPException, Request

from app.core.redis import check_rate_limit

load_dotenv()

# Rate limit 的預設設定。
DEFAULT_RATE_LIMIT = int(os.getenv("DEFAULT_RATE_LIMIT", "5"))
DEFAULT_RATE_LIMIT_WINDOW = int(os.getenv("DEFAULT_RATE_LIMIT_WINDOW", "60"))


# 建立限流 dependency：FastAPI 自己注入 Request，沒有 decorator 時代
# 「endpoint 必須宣告 request: Request 否則第一個請求 KeyError」的隱形契約。
# 用法：@router.post("/x", dependencies=[Depends(rate_limit(limit=30))])
# key 以 URL path 為界（同一路徑同一桶），client IP 為輔。
def rate_limit(
    limit: int = DEFAULT_RATE_LIMIT,
    window: int = DEFAULT_RATE_LIMIT_WINDOW,
):
    def check(request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"

        rate_limit_key = f"rate_limit:{request.url.path}:{client_ip}"

        if not check_rate_limit(rate_limit_key, limit=limit, window=window):
            raise HTTPException(status_code=429, detail="Too many requests")

    return check
