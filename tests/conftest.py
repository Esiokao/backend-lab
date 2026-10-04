# tests/conftest.py

import pytest

from app.core.redis import redis_client
from app.database import get_db
from app.main import app

# Load client fixtures.
from tests.fixtures.client import *

# Load database fixtures.
from tests.fixtures.database import *

# Load order fixtures.
from tests.fixtures.orders import *

# Load user fixtures.
from tests.fixtures.users import *


@pytest.fixture(autouse=True)
def clear_rate_limit():
    # 測試開始前清除 rate limit keys。
    for key in redis_client.scan_iter(match="rate_limit:*"):
        redis_client.delete(key)

    yield

    # 測試結束後清除 rate limit keys。
    for key in redis_client.scan_iter(match="rate_limit:*"):
        redis_client.delete(key)


# Database Fixtures


@pytest.fixture
def override_get_db(test_db):
    # 測試時讓 FastAPI 使用 transaction session。
    def _override_get_db():
        yield test_db

    # 將正式 DB dependency 替換成測試 DB。
    app.dependency_overrides[get_db] = _override_get_db

    yield

    # 測試結束後移除 override。
    app.dependency_overrides.pop(get_db, None)
