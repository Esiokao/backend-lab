# tests/admin/integration/test_admin_users.py
# Admin 使用者管理：role 編輯、email 更新、衝突與防呆。

from app.models import User


def test_admin_can_promote_user_to_admin(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_db,
):
    # 建立管理員與一般使用者。
    create_test_user(**test_admin_user_data)
    target = create_test_user(**test_user_data)

    client = session_auth_client(test_admin_user_data)

    # admin 將使用者提升為 admin。
    response = client.patch(f"/admin/users/{target.id}", json={"role": "admin"})

    assert response.status_code == 200
    assert response.json()["role"] == "admin"

    # 資料庫中的 role 也已更新。
    db_user = test_db.get(User, target.id)
    assert db_user.role == "admin"


def test_admin_can_update_user_email(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
):
    # 建立管理員與目標使用者。
    create_test_user(**test_admin_user_data)
    target = create_test_user(**test_user_data)

    client = session_auth_client(test_admin_user_data)

    response = client.patch(
        f"/admin/users/{target.id}",
        json={"email": "promoted@example.com"},
    )

    assert response.status_code == 200
    assert response.json()["email"] == "promoted@example.com"


def test_admin_cannot_change_own_role(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_db,
):
    # 建立管理員。
    admin = create_test_user(**test_admin_user_data)

    client = session_auth_client(test_admin_user_data)

    # admin 嘗試降級自己的 role → 400（避免把自己鎖在門外）。
    response = client.patch(f"/admin/users/{admin.id}", json={"role": "user"})

    assert response.status_code == 400
    assert response.json()["detail"] == "Cannot change your own role"


def test_admin_patch_email_conflict_returns_409(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
    test_random_user_data,
):
    # 建立管理員與兩位使用者。
    create_test_user(**test_admin_user_data)
    user_a = create_test_user(**test_user_data)
    user_b = create_test_user(**test_random_user_data)

    client = session_auth_client(test_admin_user_data)

    # 把 user_b 的 email 改成 user_a 的 → 409。
    response = client.patch(
        f"/admin/users/{user_b.id}",
        json={"email": user_a.email},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == "Email already exists"


def test_admin_patch_nonexistent_user_returns_404(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
):
    # 建立管理員並透過 Session 登入。
    create_test_user(**test_admin_user_data)
    client = session_auth_client(test_admin_user_data)

    response = client.patch("/admin/users/999999", json={"role": "admin"})

    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_non_admin_cannot_patch_users(
    session_auth_client,
    create_test_user,
    test_admin_user_data,
    test_user_data,
):
    # 建立管理員與一般使用者。
    admin = create_test_user(**test_admin_user_data)
    create_test_user(**test_user_data)

    # 一般使用者透過 Session 登入。
    client = session_auth_client(test_user_data)

    # 嘗試修改管理員 → 403。
    response = client.patch(f"/admin/users/{admin.id}", json={"name": "Hacked"})

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"
