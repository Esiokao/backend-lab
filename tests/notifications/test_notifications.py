from datetime import datetime, timezone


def test_list_notifications_returns_empty_list_for_unauthenticated_user(test_client):
    response = test_client.get("/notifications/")

    assert response.status_code == 401


def test_list_notifications_returns_empty_list_for_authenticated_user(
    test_client,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    # 建立使用者，並取得登入後的測試 client
    create_test_user(**test_user_data)
    auth_client = session_auth_client(test_user_data)

    response = auth_client.get("/notifications/")

    assert response.status_code == 200
    assert response.json() == {
        "items": [],
        "next_cursor": None,
    }


def test_list_notifications_only_returns_current_users_notifications(
    test_db,
    create_test_user,
    test_user_data,
    test_random_user_data,
    session_auth_client,
    create_test_notification,
):
    # 建立兩位不同的使用者
    user_a = create_test_user(**test_user_data)
    user_b = create_test_user(**test_random_user_data)

    # 分別建立兩位使用者的通知
    notification_a = create_test_notification(
        user_id=user_a.id,
        title="User A notification",
    )
    create_test_notification(
        user_id=user_b.id,
        title="User B notification",
    )

    # 以 User A 的身分呼叫通知 API
    auth_client = session_auth_client(test_user_data)
    response = auth_client.get("/notifications/")

    assert response.status_code == 200

    # 驗證回傳的通知只屬於 User A
    body = response.json()
    assert len(body["items"]) == 1
    assert body["items"][0]["id"] == notification_a.id
    assert body["items"][0]["title"] == "User A notification"
    assert all(item["title"] != "User B notification" for item in body["items"])


def test_list_notifications_rejects_invalid_cursor(
    test_user_data,
    create_test_user,
    session_auth_client,
):
    # 建立使用者並登入
    create_test_user(**test_user_data)
    auth_client = session_auth_client(test_user_data)

    response = auth_client.get(
        "/notifications/",
        params={"cursor": "not-a-valid-cursor"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid cursor"


def test_list_notifications_rejects_limit_out_of_range(
    test_user_data,
    create_test_user,
    session_auth_client,
):
    # 建立使用者並登入
    create_test_user(**test_user_data)
    auth_client = session_auth_client(test_user_data)

    # limit 最小值為 1，因此 0 應被拒絕
    response = auth_client.get(
        "/notifications/",
        params={"limit": 0},
    )

    assert response.status_code == 422


def test_list_notifications_paginates_when_created_at_is_identical(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
    create_test_notification,
):
    # Arrange: 建立三筆建立時間完全相同的通知。
    user = create_test_user(**test_user_data)
    notifications = [
        create_test_notification(
            user_id=user.id,
            title=f"Notification {index}",
        )
        for index in range(1, 4)
    ]

    fixed_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for notification in notifications:
        notification.created_at = fixed_time

    test_db.flush()

    auth_client = session_auth_client(test_user_data)

    # Act: 每頁取兩筆，分別取得第一頁與第二頁。
    first_response = auth_client.get(
        "/notifications/",
        params={"limit": 2},
    )

    assert first_response.status_code == 200
    first_page = first_response.json()

    assert len(first_page["items"]) == 2
    assert first_page["next_cursor"] is not None

    second_response = auth_client.get(
        "/notifications/",
        params={
            "limit": 2,
            "cursor": first_page["next_cursor"],
        },
    )

    assert second_response.status_code == 200
    second_page = second_response.json()

    # Assert: 同時間的通知依照 id DESC 排序，且跨頁不重複、不漏資料。
    expected_ids = sorted(
        [notification.id for notification in notifications],
        reverse=True,
    )
    first_ids = [item["id"] for item in first_page["items"]]
    second_ids = [item["id"] for item in second_page["items"]]

    assert first_ids == expected_ids[:2]
    assert second_ids == expected_ids[2:]
    assert second_page["next_cursor"] is None
    assert set(first_ids).isdisjoint(second_ids)
    assert first_ids + second_ids == expected_ids


def test_mark_notification_as_read(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
    create_test_notification,
):
    # Arrange: 建立使用者與尚未讀取的通知。
    user = create_test_user(**test_user_data)
    notification = create_test_notification(
        user_id=user.id,
        title="Unread notification",
    )
    auth_client = session_auth_client(test_user_data)

    # Act: 將通知標記為已讀。
    response = auth_client.patch(f"/notifications/{notification.id}/read")

    # Assert: API 成功回傳通知 ID 與已讀時間。
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == notification.id
    assert body["read_at"] is not None

    # 確認資料庫中的已讀狀態也已更新。
    test_db.refresh(notification)
    assert notification.read_at is not None


def test_mark_notification_as_read_is_idempotent(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
    create_test_notification,
):
    # Arrange: 建立使用者與通知。
    user = create_test_user(**test_user_data)
    notification = create_test_notification(user_id=user.id)
    auth_client = session_auth_client(test_user_data)

    # Act: 第一次標記已讀。
    first_response = auth_client.patch(f"/notifications/{notification.id}/read")
    assert first_response.status_code == 200
    first_read_at = first_response.json()["read_at"]

    # Act: 第二次重複標記已讀。
    second_response = auth_client.patch(f"/notifications/{notification.id}/read")

    # Assert: 已讀時間維持第一次的值。
    assert second_response.status_code == 200
    assert second_response.json()["read_at"] == first_read_at

    test_db.refresh(notification)
    assert notification.read_at.isoformat().replace("+00:00", "Z") == (
        first_read_at.replace("+00:00", "Z")
    )


def test_user_cannot_mark_another_users_notification_as_read(
    test_db,
    create_test_user,
    test_user_data,
    test_random_user_data,
    session_auth_client,
    create_test_notification,
):
    # Arrange：建立使用者 A、B，以及屬於 B 的通知。
    _user_a = create_test_user(**test_user_data)
    user_b = create_test_user(**test_random_user_data)

    notification = create_test_notification(user_id=user_b.id)
    auth_client = session_auth_client(test_user_data)

    # Act：使用者 A 嘗試標記使用者 B 的通知為已讀。
    response = auth_client.patch(f"/notifications/{notification.id}/read")

    # Assert：API 不應暴露或允許操作其他使用者的通知。
    assert response.status_code == 404

    # 確認資料庫中的通知仍然未讀。
    test_db.refresh(notification)
    assert notification.read_at is None


def test_mark_nonexistent_notification_as_read(
    test_user_data,
    create_test_user,
    session_auth_client,
):
    # Arrange：建立登入使用者，但不建立任何通知。
    create_test_user(**test_user_data)
    auth_client = session_auth_client(test_user_data)

    # Act：嘗試標記不存在的通知。
    response = auth_client.patch("/notifications/999999/read")

    # Assert：不存在的通知應回傳 404。
    assert response.status_code == 404
    assert response.json()["detail"] == "Notification not found"


def test_get_unread_notification_count(
    create_test_user,
    test_user_data,
    session_auth_client,
    create_test_notification,
):
    # Arrange：建立使用者，並建立兩筆未讀、一筆已讀通知。
    user = create_test_user(**test_user_data)
    create_test_notification(user_id=user.id)
    create_test_notification(user_id=user.id)
    create_test_notification(
        user_id=user.id,
        read_at=datetime.now(timezone.utc),
    )

    auth_client = session_auth_client(test_user_data)

    # Act：查詢未讀通知數量。
    response = auth_client.get("/notifications/unread-count")

    # Assert：只有兩筆通知尚未讀取。
    assert response.status_code == 200
    assert response.json() == {"unread_count": 2}


def test_unread_notification_count_only_includes_current_user(
    create_test_user,
    test_user_data,
    test_random_user_data,
    session_auth_client,
    create_test_notification,
):
    # Arrange：建立兩個使用者，A 有一筆未讀，B 有兩筆未讀。
    user_a = create_test_user(**test_user_data)
    user_b = create_test_user(**test_random_user_data)

    create_test_notification(user_id=user_a.id)
    create_test_notification(user_id=user_b.id)
    create_test_notification(user_id=user_b.id)

    auth_client = session_auth_client(test_user_data)

    # Act：使用者 A 查詢自己的未讀通知數量。
    response = auth_client.get("/notifications/unread-count")

    # Assert：只計算使用者 A 的一筆通知。
    assert response.status_code == 200
    assert response.json() == {"unread_count": 1}


def test_unread_notification_count_returns_zero_when_all_are_read(
    create_test_user,
    test_user_data,
    session_auth_client,
    create_test_notification,
):
    # Arrange：建立使用者，並建立一筆已讀通知。
    user = create_test_user(**test_user_data)
    create_test_notification(
        user_id=user.id,
        read_at=datetime.now(timezone.utc),
    )
    auth_client = session_auth_client(test_user_data)

    # Act：查詢未讀通知數量。
    response = auth_client.get("/notifications/unread-count")

    # Assert：沒有未讀通知時，數量應為 0。
    assert response.status_code == 200
    assert response.json() == {"unread_count": 0}


def test_unread_notification_count_requires_authentication(test_client):
    # Act：未登入，直接查詢未讀通知數量。
    response = test_client.get("/notifications/unread-count")

    # Assert：未登入的請求應被拒絕。
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_mark_all_notification_as_read(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
    create_test_notification,
):
    # Arrange: 建立使用者與尚未讀取的通知。
    user = create_test_user(**test_user_data)
    notification = create_test_notification(
        user_id=user.id,
        title="Unread notification",
    )
    auth_client = session_auth_client(test_user_data)

    # Act: 將通知標記為已讀。
    response = auth_client.patch(f"/notifications/{notification.id}/read")

    # Assert: API 成功回傳通知 ID 與已讀時間。
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == notification.id
    assert body["read_at"] is not None

    # 確認資料庫中的已讀狀態也已更新。
    test_db.refresh(notification)
    assert notification.read_at is not None
