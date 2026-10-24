# tests/stats/test_stats.py
# GET /stats：儀表板真實數據，admin 全站範圍、一般使用者個人範圍。


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
