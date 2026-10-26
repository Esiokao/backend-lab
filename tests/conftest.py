# tests/conftest.py

import os
import socket

# 測試使用 HTTP TestClient，因此停用 Secure cookie 限制。
os.environ["COOKIE_SECURE"] = "false"

import pytest
from redis.backoff import NoBackoff
from redis.retry import Retry

from app.core.redis import redis_client
from app.database import get_db
from app.main import app

# Load client fixtures.
from tests.fixtures.client import *

# Load database fixtures.
from tests.fixtures.database import *

# Load notification fixtures.
from tests.fixtures.notifications import *

# Load order fixtures.
from tests.fixtures.orders import *

# Load product fixtures.
from tests.fixtures.products import *

# Load user fixtures.
from tests.fixtures.users import *


# 測試環境：Redis 連不上就快失敗。
# 預設的指數退避 retry 會讓每個觸碰 Redis 的 autouse fixture
# 卡數十秒 → 整套測試假死（本機沒起 redis 時必炸）。
redis_client.set_retry(Retry(NoBackoff(), 1))


def _redis_reachable() -> bool:
    """快探測（1s timeout）：Redis 是否可達。

    不直接 ping redis_client —— 連線失敗仍會抛 ConnectionError，
    這裡用 socket 探測保持 fixture 本身零依賴。
    """

    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))

    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


@pytest.fixture(autouse=True)
def clear_rate_limit():
    # Redis 不在（本機只跑純單元測試）→ 沒有 rate limit 狀態可清，靜默略過。
    if not _redis_reachable():
        yield
        return

    # 測試開始前清除 rate limit keys。
    for key in redis_client.scan_iter(match="rate_limit:*"):
        redis_client.delete(key)

    yield

    # 測試結束後清除 rate limit keys。
    for key in redis_client.scan_iter(match="rate_limit:*"):
        redis_client.delete(key)


# Database Fixtures


@pytest.fixture
def override_get_db(test_db, monkeypatch):
    # 測試時讓 FastAPI 使用 transaction session。
    def _override_get_db():
        yield test_db

    # 將正式 DB dependency 替換成測試 DB。
    # monkeypatch.setitem 會自動還原原狀（含「本來沒有 override」的情況）。
    monkeypatch.setitem(app.dependency_overrides, get_db, _override_get_db)

    yield
