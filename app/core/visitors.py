"""匿名訪客追蹤（v1.14）：

只計「真實訪客」＝瀏覽器的文件導航（Accept: text/html）。
curl / fetch / XHR / 健康探測的 Accept 是 */*，一律不計，
避免自動化與監控流量灌水。vid 存 bl_vid cookie（一年），
計入 Redis 每日集合 visitors:<date>（SCARD = 唯一訪客數）。
"""

import secrets
from datetime import date

VISITOR_COOKIE = "bl_vid"
VISITOR_TTL_SECONDS = 2 * 24 * 60 * 60  # 集合保留兩天，過期自動清

# 不計入訪客的路徑（機器人／探測器）。
_EXCLUDED_PATHS = {"/health", "/ready"}


def is_document_request(accept_header: str | None, path: str) -> bool:
    """真人導航＝瀏覽器要 HTML。API/fetch/curl 都帶 */*，直接排除。"""
    if path in _EXCLUDED_PATHS or path.startswith("/api"):
        return False
    return accept_header is not None and "text/html" in accept_header


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
