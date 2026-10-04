def test_get_order_with_invalid_token(
    test_client,
    create_test_user,
    create_test_order,
    test_user_data,
):
    # 建立測試 User。
    user = create_test_user(**test_user_data)

    # 建立 User 的 Order。
    order = create_test_order(user.id)

    # 使用無效的 JWT。
    test_client.headers.update({"Authorization": "Bearer invalid-token"})

    # 嘗試取得 Order。
    response = test_client.get(f"/orders/{order.id}")

    # 無效 JWT 應該被拒絕。
    assert response.status_code == 401
