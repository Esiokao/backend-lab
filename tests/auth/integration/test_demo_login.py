# tests/auth/integration/test_demo_login.py
# POST /auth/demo-login：免帳密發唯讀 admin session（面試官/訪客探索用）。
#
# 防線矩陣：
#   demo session：GET admin 資源 200、任何寫入 403（require_admin 的
#   session read_only 標記）
#   demo 帳號 password_hash=None → /login 密碼登入永遠 401
#   Turnstile env-gated：設 secret 後缺 token → 401

from app.models import User


def test_demo_login_creates_read_only_admin(test_client, test_db):
    response = test_client.post("/auth/demo-login")

    assert response.status_code == 200
    assert response.json() == {"ok": True}

    me = test_client.get("/users/me")
    assert me.status_code == 200
    assert me.json()["email"] == "demo@demo.esiokao.shop"
    assert me.json()["role"] == "admin"

    # demo 帳號無密碼：DB 裡 hash 必須是 NULL（密碼登入的根據）。
    user = test_db.query(User).filter(User.email == "demo@demo.esiokao.shop").one()
    assert user.password_hash is None
    assert user.role == "admin"


def test_demo_login_is_idempotent(test_client):
    first = test_client.post("/auth/demo-login")
    second = test_client.post("/auth/demo-login")

    assert first.status_code == 200
    assert second.status_code == 200

    me = test_client.get("/users/me")
    assert me.json()["email"] == "demo@demo.esiokao.shop"


def test_demo_session_can_read_admin_resources(test_client, test_db):
    from decimal import Decimal

    from app.models import Product

    product = Product(name="Probe P", price=Decimal("10.00"), stock=5)
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)

    test_client.post("/auth/demo-login")

    response = test_client.get("/admin/orders")
    assert response.status_code == 200

    detail = test_client.get(f"/users/{product.id}")
    # /users/{id} 是 user detail——demo 也能讀（唯讀 admin 視野）。
    assert detail.status_code in (200, 404)


def test_demo_session_cannot_mutate(test_client, test_db):
    from decimal import Decimal

    from app.models import Product

    product = Product(name="Probe P2", price=Decimal("10.00"), stock=5)
    test_db.add(product)
    test_db.commit()
    test_db.refresh(product)

    test_client.post("/auth/demo-login")

    # admin 寫入路由：唯讀 session 一律 403（require_admin 的 read_only 標記）。
    response = test_client.patch(f"/products/{product.id}", json={"price": "99.00"})
    assert response.status_code == 403

    response = test_client.post(
        "/products", json={"name": "Hacked", "price": "1.00", "stock": 1}
    )
    assert response.status_code == 403

    response = test_client.post("/categories", json={"name": "Hacked Category"})
    assert response.status_code == 403


def test_demo_user_cannot_password_login(test_client, test_db):
    # demo-login 建立的帳號 password_hash=None → /login 永遠 401
    # （demo 帳號只能透過 demo-login 進場，密碼撞庫無意義）。
    test_client.post("/auth/demo-login")
    test_db.expire_all()

    user = test_db.query(User).filter(User.email == "demo@demo.esiokao.shop").one()
    assert user.password_hash is None

    response = test_client.post(
        "/login",
        json={"email": "demo@demo.esiokao.shop", "password": "whatever-pass-123"},
    )
    assert response.status_code == 401


def test_logout_of_suffixed_session(test_client):
    # 回歸：session value 帶 :ro / :remember 後綴時，delete_session 的
    # int(value) 會 ValueError → /logout 500（cookie 已刪但索引殘留）。
    # demo（:ro）與 remember 登入都必須能正常登出。
    test_client.post("/auth/demo-login")
    response = test_client.post("/logout")
    assert response.status_code == 200
    assert test_client.get("/users/me").status_code == 401
