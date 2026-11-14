"""匿名訪客追蹤（v2.6）：

只計「真實訪客」＝SPA 成功啟動（前端 mount 時 POST /visitors/track 報到）。
curl / 爬蟲 / 健康探測不執行 JS，天然不會報到。
vid 存 bl_vid cookie（一年），計入 Redis 每日集合 visitors:<date>
（SCARD = 唯一訪客數）與全量 HyperLogLog（PFCOUNT = 歷史總數）。

歷史：v1.14 曾以「Accept: text/html 的文件請求」定義訪客（middleware
判定），但 frontend 拆成靜態容器後文件請求不再經過 FastAPI，指標
結構性歸零——v2.6 改為前端主動報到，本模組的計數邏輯不變。
"""

import secrets
from datetime import date, datetime

VISITOR_COOKIE = "bl_vid"
VISITOR_TTL_SECONDS = 2 * 24 * 60 * 60  # 集合保留兩天，過期自動清


TOTAL_HLL_KEY = "visitors:hll:total"

# 全量唯一訪客走 HyperLogLog：固定 12KB、誤差 ~0.81%，
# 訪客成長到百萬也不漲記憶體——總數指標的正確工具。
# （要歷史趨勢/回訪分析才值得另開 DB 表。）


def _day_key(day: date) -> str:
    return f"visitors:{day.isoformat()}"


def _today() -> date:
    """訪客計數的「今天」：本地時區的日期（統計頁給人看的日界）。

    不用 date.today()（ruff DTZ011）、也不用 UTC（深夜會跟本地日錯開），
    以本機時區取當下日期。
    """
    return datetime.now().astimezone().date()


def track_visitor(redis, cookie_value: str | None) -> str:
    """回傳該訪客的 vid（既有或新建）；計入今日集合與全量 HLL。"""
    vid = cookie_value or secrets.token_hex(16)
    key = _day_key(_today())
    redis.sadd(key, vid)
    redis.expire(key, VISITOR_TTL_SECONDS)
    redis.pfadd(TOTAL_HLL_KEY, vid)
    return vid


def visitors_today_count(redis) -> int:
    return int(redis.scard(_day_key(_today())))


def visitors_total_count(redis) -> int:
    return int(redis.pfcount(TOTAL_HLL_KEY))
