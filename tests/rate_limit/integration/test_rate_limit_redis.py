"""Rate limit 整合測試——真 Redis，不打 mock。

unit tests（test_redis.py）mock 掉 eval，只驗證包裝函式的分支邏輯；
這裡補上引擎層：Lua script 的連續計數、TTL、key 隔離與並發原子性。

四步骨架：
① 不變量：每 60 秒每 key 最多 limit 次放行；TTL 恆存在
② 注入：連打 limit+2 次、並發 limit+3 個執行緒、不同 key 交叉
③ 斷言：前 limit 次 True、之後 False、TTL ∈ (0, 60]、放行數精確
④ 穩定：key 用 uuid（測試間隔離）、barrier 保證真並發、不 sleep
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from app.core.rate_limit import check_rate_limit
from app.core.redis import redis_client


def _unique_key() -> str:
    # uuid 隔離：不撞其他測試的 rate_limit key，跑完由自身 TTL（60s）自然過期
    return f"rate_limit:integration:{uuid.uuid4().hex}"


def test_rate_limit_allows_up_to_limit_then_blocks():
    # 不變量 ①：前 limit 次放行，之後全部拒絕
    key = _unique_key()
    limit = 3
    results = [check_rate_limit(key, limit=limit, window=60) for _ in range(limit + 2)]

    assert results[:limit] == [True] * limit
    assert results[limit:] == [False] * (len(results) - limit)


def test_rate_limit_sets_ttl_on_first_hit():
    # BUG 2 回歸守衛：TTL 必須在首次計數時設立，且後續請求不移除（NX 語意）
    key = _unique_key()
    check_rate_limit(key, limit=5, window=60)

    ttl = redis_client.ttl(key)
    assert 0 < ttl <= 60

    check_rate_limit(key, limit=5, window=60)
    assert redis_client.ttl(key) > 0  # NX 不會把已存在的 TTL 洗掉


def test_rate_limit_keys_are_isolated():
    # 不變量 ②：不同 key（不同 IP/endpoint）各自獨立計數
    k1, k2 = _unique_key(), _unique_key()

    assert check_rate_limit(k1, limit=1, window=60) is True
    assert check_rate_limit(k1, limit=1, window=60) is False  # k1 超限
    assert check_rate_limit(k2, limit=1, window=60) is True  # k2 不受牽連


def test_rate_limit_is_atomic_under_concurrency():
    # 不變量 ③：並發下放行數精確等於 limit——Lua 原子性的行為證明
    key = _unique_key()
    limit = 5
    workers = limit + 3  # 故意超發，驗證精確擋下
    barrier = threading.Barrier(workers)

    def hit():
        barrier.wait()  # 全部就緒後同時起跑
        return check_rate_limit(key, limit=limit, window=60)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        results = list(pool.map(lambda _: hit(), range(workers)))

    assert results.count(True) == limit
    assert results.count(False) == workers - limit
