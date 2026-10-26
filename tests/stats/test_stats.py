# tests/stats/test_stats.py
# GET /stats：儀表板真實數據，admin 全站範圍、一般使用者個人範圍。


def test_admin_stats_include_revenue_excluding_cancelled(
    session_auth_client,
    create_test_user,
    create_test_order,
    create_test_product,
    test_admin_user_data,
    test_user_data,
):
    from decimal import Decimal

    create_test_user(**test_admin_user_data)
    buyer = create_test_user(**test_user_data)
    sweater = create_test_product(name="Sweater", price=Decimal("100.00"), stock=10)
    mug = create_test_product(name="Mug", price=Decimal("34.00"), stock=10)

    paid = create_test_order(user_id=buyer.id, product=sweater, quantity=2)  # $200
    paid.status = "pending"  # 未取消 → 計入
    cancelled = create_test_order(user_id=buyer.id, product=mug, quantity=1)  # $34
    cancelled.status = "cancelled"  # 取消 → 不計

    client = session_auth_client(test_admin_user_data)

    # 明確種一個訪客：帶 Accept: text/html 的文件導航請求（middleware 只計這種）。
    # TestClient 預設 accept 是 */* → 不會被計入；沒有這步，全新 Redis 上
    # visitors_total 恆為 0（本地會過是因為 Redis 有歷史訪客 —— 共享狀態依賴）。
    client.get("/nonexistent", headers={"Accept": "text/html"})

    response = client.get("/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["total_revenue"] == 200.0
    assert body["revenue_today"] == 200.0
    assert "visitors_today" in body
    assert "visitors_total" in body
    assert body["visitors_total"] >= 1  # 上面的導航請求已計入 HLL


def test_admin_stats_reflect_global_counts(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_admin_user_data,
    test_user_data,
):
    create_test_user(**test_admin_user_data)
    other = create_test_user(**test_user_data)
    create_test_order(user_id=other.id)
    create_test_order(user_id=other.id)

    client = session_auth_client(test_admin_user_data)
    response = client.get("/stats")

    assert response.status_code == 200
    body = response.json()

    assert body["scope"] == "global"
    assert body["total_users"] >= 2  # admin 自己 + other
    assert body["total_orders"] >= 2
    assert body["orders_today"] >= 2  # 剛建立的訂單都是今天


def test_user_stats_are_personal(
    session_auth_client,
    create_test_user,
    create_test_order,
    test_user_data,
    test_random_user_data,
):
    me = create_test_user(**test_user_data)
    create_test_order(user_id=me.id)

    someone_else = create_test_user(**test_random_user_data)
    create_test_order(user_id=someone_else.id)

    client = session_auth_client(test_user_data)
    response = client.get("/stats")

    assert response.status_code == 200
    body = response.json()

    assert body["scope"] == "personal"
    # 只算自己的：別人的訂單不計入。
    assert body["total_orders"] == 1
    assert body["orders_today"] == 1
    assert body["unread_notifications"] == 0


def test_unauthenticated_cannot_read_stats(test_client):
    response = test_client.get("/stats")
    assert response.status_code == 401


def test_visitor_tracking_only_counts_document_requests(test_client):
    # v1.14：只計 Accept: text/html 的瀏覽器導航；curl/fetch 一律不計。
    from app.core.redis import redis_client
    from app.core.visitors import is_document_request

    # 單元：判定函數
    assert is_document_request("text/html,application/xhtml+xml", "/") is True
    assert is_document_request("*/*", "/") is False  # curl / fetch
    assert is_document_request("text/html", "/api/products") is False  # API 路徑
    assert is_document_request("text/html", "/health") is False  # 探測
    assert is_document_request(None, "/") is False

    # 整合：瀏覽器導航會計入、curl 不會
    before = int(
        redis_client.scard(
            f"visitors:{__import__('datetime').date.today().isoformat()}"
        )
    )
    test_client.get("/", headers={"Accept": "text/html"})
    test_client.get("/", headers={"Accept": "*/*"})  # 模擬 curl
    after = int(
        redis_client.scard(
            f"visitors:{__import__('datetime').date.today().isoformat()}"
        )
    )
    assert after == before + 1  # 只有 text/html 那次計入
