import os
import secrets
from datetime import timedelta

from app.core.redis import redis_client

# Session 有效期；每次成功驗證會續期（滑動過期），閒置超過 TTL 才失效。
SESSION_TTL_SECONDS = int(timedelta(days=7).total_seconds())

# 「Keep me signed in」的加長有效期；滑動續期同樣適用——
# 只要在 30 天內有活動就一直續，閒置 30 天才失效。
REMEMBER_TTL_SECONDS = int(timedelta(days=30).total_seconds())

# 與 rate_limit 的 key 空間分開。
SESSION_PREFIX = "session:"

# 使用者擁有的 session 索引前綴：user:{uid}:sessions（Redis SET，存 sid）。
USER_SESSIONS_PREFIX = "user:"
USER_SESSIONS_SUFFIX = ":sessions"

# 瀏覽器 cookie 名稱。
COOKIE_NAME = "session"


def cookie_secure() -> bool:
    """cookie 的 Secure flag。

    production 走 https，預設 true；
    測試的 TestClient 走 http，httpx 不會送 Secure cookie，需要 false。
    """
    return os.getenv("COOKIE_SECURE", "true").lower() == "true"


def user_sessions_key(user_id: int) -> str:
    """回傳該使用者的 session 索引 key。"""
    return f"{USER_SESSIONS_PREFIX}{user_id}{USER_SESSIONS_SUFFIX}"


def create_session(user_id: int, *, ttl_seconds: int = SESSION_TTL_SECONDS) -> str:
    """建立 session，回傳不透明 session id。

    id 由 secrets 產生（128-bit entropy），本身不含任何資料；
    真正的 user_id 存在 Redis，隨時可刪除 = 隨時可撤銷。
    remember 版 session 的 value 帶 :remember 後綴，讓滑動續期
    （get_session_user_id）知道要用加長 TTL，不會被縮回 7 天。
    """
    sid = secrets.token_urlsafe(32)

    value = str(user_id)
    if ttl_seconds == REMEMBER_TTL_SECONDS:
        value = f"{value}:remember"

    redis_client.set(
        f"{SESSION_PREFIX}{sid}",
        value,
        ex=ttl_seconds,
    )

    # 把 sid 加入使用者的 session 索引，索引本身也設同樣 TTL。
    index_key = user_sessions_key(user_id)
    redis_client.sadd(index_key, sid)
    redis_client.expire(index_key, ttl_seconds)

    return sid


def get_session_user_id(sid: str) -> int | None:
    """用 sid 查 user_id；查到的同時滑動續期（含使用者 session 索引）。"""
    key = f"{SESSION_PREFIX}{sid}"

    value = redis_client.get(key)

    if value is None:
        return None

    user_id_str, _, remember = value.partition(":")
    user_id = int(user_id_str)

    # 滑動過期：活躍使用者的 session 不會過期，閒置超過 TTL 才失效。
    # remember 版用加長 TTL 續期；索引也要一起續期，否則活躍 session
    # 會因索引過期而躲過 revoke。
    ttl = REMEMBER_TTL_SECONDS if remember == "remember" else SESSION_TTL_SECONDS
    redis_client.expire(key, ttl)
    redis_client.expire(user_sessions_key(user_id), ttl)

    return user_id


def delete_session(sid: str) -> None:
    """刪除 session（登出 / 撤銷），立即生效。"""
    key = f"{SESSION_PREFIX}{sid}"

    # 先查出 uid，才能一併從使用者的 session 索引移除。
    value = redis_client.get(key)

    redis_client.delete(key)

    # 索引內沒有該 sid 時 srem 只是回傳 0，不影響正確性。
    if value is not None:
        redis_client.srem(user_sessions_key(int(value)), sid)


def revoke_all_user_sessions(user_id: int) -> int:
    """撤銷該使用者的全部 session，回傳刪除的 session 數量。"""
    index_key = user_sessions_key(user_id)

    # 取出該使用者目前所有的 sid。
    sids = redis_client.smembers(index_key)

    if not sids:
        # 沒有索引紀錄就直接刪索引 key（可能已過期，不算錯誤）。
        redis_client.delete(index_key)
        return 0

    # 逐一刪除 session key，最後刪除索引本身。
    keys = [f"{SESSION_PREFIX}{sid}" for sid in sids]
    keys.append(index_key)
    redis_client.delete(*keys)

    return len(sids)
