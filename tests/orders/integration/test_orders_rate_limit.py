# tests/orders/integration/test_orders_rate_limit.py
# 建單限流（30 次/分鐘/IP）：縱深防禦的保險絲——真正的庫存鎖死由過期 worker 根治。

from decimal import Decimal

from app.core.redis import redis_client
from app.models import Product

LIMIT = 30


def _clear_order_rate_limit():
    # TestClient 的 IP 固定是 "testclient"——先清掉其他測試累積的計數，
    # 讓這條測試的限流狀態從零開始（Redis 不吃 test_db 的 rollback）。
    for key in redis_client.scan_iter("rate_limit:create_order:*"):
        redis_client.delete(key)


def test_create_order_is_rate_limited(
    test_db, create_test_user, test_user_data, session_auth_client
):
    _clear_order_rate_limit()

    create_test_user(**test_user_data)
    product = Product(
        name="Coffee Beans",
        price=Decimal("1.00"),
        stock=1000,  # 量要夠：讓 30 次建單都不會碰到庫存不足（那會回 409 而非 429）
        is_active=True,
    )
    test_db.add(product)
    test_db.flush()

    auth_client = session_auth_client(test_user_data)
    payload = {"items": [{"product_id": product.id, "quantity": 1}]}

    # 前 30 次：全部放行
    codes = [
        auth_client.post("/orders", json=payload).status_code for _ in range(LIMIT)
    ]
    assert all(code == 200 for code in codes), codes

    # 第 31 次：429
    response = auth_client.post("/orders", json=payload)
    assert response.status_code == 429
