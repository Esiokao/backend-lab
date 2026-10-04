# tests/unit/test_rbac.py

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from fastapi import HTTPException

from app.core.dependencies import require_admin
from app.routers.orders import get_users_with_orders


def test_require_admin_forbidden(
    create_test_user,
    test_user_data,
):
    # 使用測試資料建立一般 User。
    user = create_test_user(**test_user_data)

    # 一般 User 不應該通過 admin 檢查。
    with pytest.raises(HTTPException) as exc_info:
        require_admin(current_user=user)

    # 一般 User 應該收到 403。
    assert exc_info.value.status_code == 403


def test_require_admin_success(
    create_test_user,
    test_admin_user_data,
):
    # 使用測試資料建立 Admin User。
    admin = create_test_user(**test_admin_user_data)

    # Admin 應該通過權限檢查。
    user = require_admin(current_user=admin)

    # 確認回傳的就是原本的 User。
    assert user is admin


def test_get_users_with_orders_admin(
    create_test_user, test_admin_user_data, auth_client
):
    # create admin
    create_test_user(**test_admin_user_data)

    # login get beacon

    client = auth_client(test_admin_user_data)

    response = client.get("/users-with-orders")

    assert response.status_code == 200


def test_unit_get_users_with_orders_admin():
    # create a fake admin user
    fake_admin_user = SimpleNamespace(
        id=1,
        name="faker",
        email="faker@test.com",
        password_hash="fake-hash",
        role="admin",
    )
    # prep the fake result
    fake_admin_user.orders = [Mock(), Mock()]

    fake_response = Mock()
    fake_response.scalars.return_value.all.return_value = [fake_admin_user]

    # prep the fake session for api
    fake_session = Mock()
    # api return fake sql orm obj
    # session.execute(...)
    fake_session.execute.return_value = fake_response

    result = get_users_with_orders(
        current_user=fake_admin_user,
        session=fake_session,
    )

    assert result == {
        "users": [
            {"name": fake_admin_user.name, "order_count": len(fake_admin_user.orders)}
        ]
    }
