# tests/notifications/test_broadcast_watermark.py
# 廣播已讀水位（v1.12）：
# - 未讀 = id > 水位 且 非使用者註冊前發布
# - read-all 把水位推到最新 → 未讀歸零
# - unread-count 合計兩種未讀

from datetime import datetime, timedelta, timezone

from app.models import NotificationBroadcast


def _broadcast(test_db, *, created_at=None):
    # 預設給「明確晚於註冊」的時間：同一交易內 now() 是交易開始時間，
    # user 與 broadcast 會拿到相同值，被嚴格 > 排除（真實世界兩者相隔很久）。
    if created_at is None:
        created_at = datetime.now(timezone.utc) + timedelta(hours=1)
    broadcast = NotificationBroadcast(
        type="admin_announcement",
        title="公告",
        body="內容",
        created_at=created_at,
    )
    test_db.add(broadcast)
    test_db.flush()
    return broadcast


def test_unread_counts_broadcasts_above_watermark(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    user = create_test_user(**test_user_data)
    old = _broadcast(test_db)
    _broadcast(test_db)
    test_db.commit()
    client = session_auth_client(test_user_data)

    response = client.get("/notifications/broadcasts")

    assert response.status_code == 200
    # 使用者沒有水位（NULL → 0）：兩則都未讀。
    assert response.json()["unread_count"] == 2

    # 推水位到第一則 → 只剩一則未讀。
    user.last_seen_broadcast_id = old.id
    test_db.commit()

    response = client.get("/notifications/broadcasts")
    assert response.json()["unread_count"] == 1


def test_broadcasts_before_signup_are_not_unread(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    # 註冊前發布的舊公告不算未讀（新使用者不該被歷史公告轟炸）。
    user = create_test_user(**test_user_data)
    pre_signup = _broadcast(
        test_db,
        created_at=user.created_at - timedelta(days=1),
    )
    test_db.commit()
    client = session_auth_client(test_user_data)

    response = client.get("/notifications/broadcasts")

    assert response.json()["unread_count"] == 0
    assert pre_signup.id > 0  # 公告存在但不在未讀內


def test_read_all_sets_watermark_to_latest(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    create_test_user(**test_user_data)
    _broadcast(test_db)
    _broadcast(test_db)
    test_db.commit()
    client = session_auth_client(test_user_data)

    response = client.post("/notifications/broadcasts/read-all")

    assert response.status_code == 200
    assert response.json()["broadcasts_unread"] == 0

    response = client.get("/notifications/broadcasts")
    assert response.json()["unread_count"] == 0

    # 水位持久化：重新查詢後仍未讀 0。
    response = client.get("/notifications/unread-count")
    assert response.json()["broadcasts_unread"] == 0


def test_read_all_on_empty_broadcasts_is_noop(
    create_test_user,
    test_user_data,
    session_auth_client,
):
    create_test_user(**test_user_data)
    client = session_auth_client(test_user_data)

    response = client.post("/notifications/broadcasts/read-all")

    assert response.status_code == 200
    assert response.json()["broadcasts_unread"] == 0


def test_unread_count_endpoint_sums_both_kinds(
    test_db,
    create_test_user,
    create_test_notification,
    test_user_data,
    session_auth_client,
):
    user = create_test_user(**test_user_data)
    _broadcast(test_db)
    _broadcast(test_db)
    create_test_notification(user_id=user.id)
    test_db.commit()
    client = session_auth_client(test_user_data)

    response = client.get("/notifications/unread-count")

    body = response.json()
    assert body["unread_count"] == 1
    assert body["broadcasts_unread"] == 2

    # 全部讀完 → 兩種都歸零。
    client.post("/notifications/broadcasts/read-all")
    client.patch("/notifications/mark_all_read")
    response = client.get("/notifications/unread-count")
    assert response.json() == {"unread_count": 0, "broadcasts_unread": 0}
