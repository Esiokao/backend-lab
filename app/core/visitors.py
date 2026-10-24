"""匿名訪客追蹤（v1.14）：

middleware 在每個請求發一顆 `bl_vid` cookie（一年效期），
並把 vid 塞進 Redis 的每日集合 `visitors:<date>`（SCARD = 唯一訪客數）。
健康探測（/health、/ready）不計，避免 uptime check 灌水。
"""

import secrets
from datetime import date

VISITOR_COOKIE = "bl_vid"
VISITOR_TTL_SECONDS = 2 * 24 * 60 * 60  # 集合保留兩天，過期自動清

# 不計入訪客的路徑（機器人／探測器）。
_EXCLUDED_PATHS = {"/health", "/ready"}


def _day_key(day: date) -> str:
    return f"visitors:{day.isoformat()}"


def track_visitor(redis, cookie_value: str | None) -> str:
    """回傳該訪客的 vid（既有或新建）；並計入今日集合。"""
    vid = cookie_value or secrets.token_hex(16)
    key = _day_key(date.today())
    redis.sadd(key, vid)
    redis.expire(key, VISITOR_TTL_SECONDS)
    return vid


def visitors_today_count(redis) -> int:
    return int(redis.scard(_day_key(date.today())))
