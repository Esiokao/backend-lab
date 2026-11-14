# app/routers/visitors.py
# 訪客報到端點（v2.6）：前端 SPA mount 時 fire-and-forget 打一發 POST。
#
# 為什麼存在：舊的 track_visitors middleware 以「Accept: text/html 的文件
# 請求」定義訪客，但 frontend 拆成靜態容器後，文件請求永遠走 edge nginx →
# frontend，不經過 FastAPI——判定機制棲地消失，指標結構性歸零。
# 新定義：「SPA 成功啟動 = 訪客」——只有真瀏覽器會執行 JS，curl／爬蟲／
# 健康探測天然不會報到。
# 計數與 cookie 邏輯原封沿用 visitors.py：SET（今日精確、兩天過期）+
# HLL（全量、固定 12KB）。

from fastapi import APIRouter, Cookie, Depends, Response

from app.core.rate_limit import rate_limit
from app.core.redis import redis_client
from app.core.visitors import VISITOR_COOKIE, track_visitor

router = APIRouter(tags=["meta"])


@router.post("/visitors/track", dependencies=[Depends(rate_limit(limit=30, window=60))])
def track(response: Response, bl_vid: str | None = Cookie(None)):
    # 冪等：同一 vid 重複報到，SET/HLL 天然去重。
    vid = track_visitor(redis_client, bl_vid)

    # 新訪客第一次報到才下發身分 cookie；回訪者帶證前來，不重複發。
    if bl_vid is None:
        response.set_cookie(
            key=VISITOR_COOKIE,
            value=vid,
            max_age=365 * 24 * 60 * 60,
            samesite="lax",
            httponly=True,
        )

    return {"ok": True}
