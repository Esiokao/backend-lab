"""SSE 即時推送端點（F11-4）。

資料流：worker 處理完通知後 PUBLISH notify:user:{id} → 本端點 SUBSCRIBE
→ 以 text/event-stream 推給瀏覽器的 EventSource。

推送只是「該刷新了」的提示，通知資料一律以 DB 為準；
pub/sub 不保證送達，漏掉的由前端 10 秒輪詢兜底。
"""

import asyncio
import os

from fastapi import Depends
from fastapi.responses import StreamingResponse
from redis import asyncio as aioredis

from app.core.dependencies import get_current_user
from app.core.events import BROADCAST_CHANNEL, user_channel
from app.core.request_size import SizeLimitedAPIRouter
from app.models import User

router = SizeLimitedAPIRouter(prefix="/notifications")

# 心跳週期：SSE 註解行（": ping"）讓中間層知道連線活著，
# 也讓 async generator 有機會被喚醒、察覺客戶端已斷開。
HEARTBEAT_SECONDS = 25


async def _event_stream(user_id: int):
    """一條瀏覽器連線 = 一個 async 產生器：訂閱 → 轉發 → 斷線清理。"""
    # redis.asyncio 是另一套 client（跟 app/core/redis.py 的同步版不同物件）；
    # 同步 client 的呼叫會凍結整個 event loop，SSE 連線必須走 async。
    redis = aioredis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        decode_responses=True,
    )
    pubsub = redis.pubsub()
    # 個人頻道（通知）＋公告頻道（廣播）：兩種來源共用同一條 SSE 連線。
    await pubsub.subscribe(user_channel(user_id), BROADCAST_CHANNEL)

    try:
        # 開場事件：前端藉此確認連線建立（也讓測試好斷言）。
        yield "event: connected\ndata: ok\n\n"

        while True:
            try:
                # get_message 本身不等待；wait_for 給它 25 秒的「等下一則」上限。
                message = await asyncio.wait_for(
                    pubsub.get_message(ignore_subscribe_messages=True),
                    timeout=HEARTBEAT_SECONDS,
                )
            except asyncio.TimeoutError:
                # 25 秒沒事件 → 推心跳。瀏覽器的 EventSource 會忽略 ": " 開頭的行。
                yield ": ping\n\n"
                continue

            if message is None:
                continue

            # PUBLISH 進來的 data 原樣轉發；事件名稱固定 notification，
            # 前端用 addEventListener("notification", ...) 接。
            yield f"event: notification\ndata: {message['data']}\n\n"
    finally:
        # 瀏覽器關分頁／斷線 → uvicorn 取消這個產生器 → 走到這裡，
        # 釋放 Redis 訂閱與連線，不會越積越多。
        await pubsub.unsubscribe(user_channel(user_id), BROADCAST_CHANNEL)
        await pubsub.aclose()
        await redis.aclose()


@router.get("/stream")
async def stream(user: User = Depends(get_current_user)):
    """即時通知推送：EventSource 同源自動帶 session cookie，沿用現有認證。"""
    return StreamingResponse(
        _event_stream(user.id),
        media_type="text/event-stream",
        headers={
            # 關閉所有層級的快取；nginx 的緩衝問題在第 7 課處理。
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
