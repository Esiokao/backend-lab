from functools import wraps  # 保留被 decorator 包裝函式的 metadata

from fastapi import HTTPException  # 用來回傳 HTTP 錯誤

from app.core.redis import check_rate_limit  # Redis rate limit 檢查


# 建立可設定限制次數與時間窗口的 decorator
def rate_limit(limit: int = 5, window: int = 60):

    # 接收真正要被包裝的 endpoint
    def decorator(func):

        # 保留原本 endpoint 的名稱與 metadata
        @wraps(func)
        def wrapper(*args, **kwargs):

            # 從 endpoint 的參數取得 Request
            request = kwargs["request"]

            # 取得 client IP
            client_ip = request.client.host

            # 取得目前 endpoint 的名稱
            endpoint_name = func.__name__

            # 建立 Redis 使用的 rate limit key
            rate_limit_key = f"rate_limit:{endpoint_name}:{client_ip}"

            # 檢查目前 request 是否還在限制範圍內
            allowed = check_rate_limit(
                rate_limit_key,
                limit=limit,
                window=window,
            )

            # 超過限制就直接回傳 429
            if not allowed:
                raise HTTPException(
                    status_code=429,
                    detail="Too many requests",
                )

            # 沒超過限制，繼續執行原本的 endpoint
            return func(*args, **kwargs)

        # 回傳包裝後的 endpoint
        return wrapper

    # 回傳 decorator
    return decorator
