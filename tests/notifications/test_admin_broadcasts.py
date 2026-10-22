from datetime import datetime, timezone

from app.models import NotificationBroadcast


def test_admin_can_create_notification_broadcast(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    admin_data = {**test_user_data, "role": "admin"}
    create_test_user(**admin_data)

    auth_client = session_auth_client(admin_data)

    response = auth_client.post(
        "/admin/notifications/broadcasts",
        json={
            "type": "admin_announcement",
            "title": "系統公告",
            "body": "今晚 23:00 維護。",
        },
    )

    assert response.status_code == 201

    body = response.json()
    assert body["type"] == "admin_announcement"
    assert body["title"] == "系統公告"
    assert body["body"] == "今晚 23:00 維護。"

    broadcast = test_db.get(
        NotificationBroadcast,
        body["id"],
    )

    assert broadcast is not None


def test_regular_user_cannot_create_notification_broadcast(
    create_test_user,
    test_user_data,
    session_auth_client,
):
    create_test_user(**test_user_data)

    auth_client = session_auth_client(test_user_data)

    response = auth_client.post(
        "/admin/notifications/broadcasts",
        json={
            "type": "admin_announcement",
            "title": "系統公告",
            "body": "測試內容",
        },
    )

    assert response.status_code == 403


def test_authenticated_user_can_list_broadcasts(
    create_test_user,
    test_user_data,
    session_auth_client,
    test_db,
):
    create_test_user(**test_user_data)

    broadcast = NotificationBroadcast(
        type="admin_announcement",
        title="系統公告",
        body="今晚 23:00 維護。",
    )
    test_db.add(broadcast)
    test_db.flush()

    auth_client = session_auth_client(test_user_data)

    response = auth_client.get("/notifications/broadcasts")

    assert response.status_code == 200
    assert response.json()["items"][0]["title"] == "系統公告"


def test_unauthenticated_user_cannot_list_broadcasts(test_client):
    response = test_client.get("/notifications/broadcasts")

    assert response.status_code == 401


def test_broadcasts_are_returned_newest_first(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    create_test_user(**test_user_data)

    older = NotificationBroadcast(
        type="admin_announcement",
        title="較舊公告",
        body="舊內容",
        created_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
    )

    newer = NotificationBroadcast(
        type="admin_announcement",
        title="最新公告",
        body="新內容",
        created_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    test_db.add_all([older, newer])
    test_db.flush()

    auth_client = session_auth_client(test_user_data)

    response = auth_client.get("/notifications/broadcasts")

    assert response.status_code == 200

    items = response.json()["items"]

    assert items[0]["title"] == "最新公告"
    assert items[1]["title"] == "較舊公告"
