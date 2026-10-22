def test_regular_user_cannot_create_admin_notification(
    test_user_data,
    create_test_user,
    session_auth_client,
):
    create_test_user(**test_user_data)
    auth_client = session_auth_client(test_user_data)

    response = auth_client.post(
        "/admin/notifications/",
        json={
            "user_id": 1,
            "title": "系統公告",
            "body": "測試通知",
        },
    )

    assert response.status_code == 403


def test_admin_can_create_notification_outbox(
    test_db,
    create_test_user,
    test_user_data,
    session_auth_client,
):
    admin_data = {**test_user_data, "role": "admin"}
    user = create_test_user(**admin_data)
    auth_client = session_auth_client(admin_data)

    response = auth_client.post(
        "/admin/notifications/",
        json={
            "user_id": user.id,
            "title": "系統公告",
            "body": "測試通知",
        },
    )

    assert response.status_code == 202
    assert response.json()["status"] == "pending"
