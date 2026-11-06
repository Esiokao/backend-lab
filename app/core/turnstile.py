"""Cloudflare Turnstile 驗證（login 的 bot 防線）。

env-gated：TURNSTILE_SECRET_KEY 有設才驗證——dev / pytest / e2e
不設 key，邏輯整段跳過（測試零改動）；正式環境設 key 即生效。
"""

import logging

import httpx
from fastapi import HTTPException

logger = logging.getLogger(__name__)

SITEVERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


async def verify_turnstile_token(token: str, remote_ip: str | None) -> None:
    """驗證 Turnstile token；失敗 raise 401。

    呼叫前請先用 turnstile_enabled() 判斷（沒設 secret 的環境直接跳過）。
    """
    import os

    secret = os.getenv("TURNSTILE_SECRET_KEY")
    if not secret:
        return

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(
                SITEVERIFY_URL,
                data={
                    "secret": secret,
                    "response": token,
                    **({"remoteip": remote_ip} if remote_ip else {}),
                },
            )
            result = response.json()
    except httpx.HTTPError:
        # Cloudflare 連不上：保守拒絕（fail closed）——bot 防線不該在
        # 故障時變成敞開的大門；使用者重試即可。
        logger.warning("Turnstile siteverify unreachable; denying login")
        raise HTTPException(status_code=503, detail="Captcha verification unavailable")

    if not result.get("success", False):
        raise HTTPException(status_code=401, detail="Captcha verification failed")
