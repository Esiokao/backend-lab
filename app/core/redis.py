import os
from pathlib import Path

import redis

redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
    decode_responses=True,
)

LUA_DIR = Path(__file__).parent / "lua"

RATE_LIMIT_SCRIPT = (LUA_DIR / "rate_limit.lua").read_text(encoding="utf-8")


def check_rate_limit(
    key: str,
    limit: int = 5,
    window: int = 60,
) -> bool:
    count = redis_client.eval(
        RATE_LIMIT_SCRIPT,
        1,
        key,
        window,
    )

    return int(count) <= limit
