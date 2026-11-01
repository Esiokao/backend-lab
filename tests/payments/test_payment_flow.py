# tests/payments/test_payment_flow.py
# 付款三步流程（intent → mock-provider → pay with receipt）的攻擊情境測試。
# 每條測試對應一個「免費商品」攻擊的變形——這套測試就是付款邊界本身。

from decimal import Decimal

from sqlalchemy import select

from app.models import PaymentIntent


def _signup_and_create_order(
    test_db, create_test_user, test_user_data, session_auth_client, price="19.99"
):
    """開一個帳號 + 透過 API 建一筆未付款訂單，回傳 (client, order_id, product)。"""
    from app.models import Product

    create_test_user(**test_user_data)
    auth_client = session_auth_client(test_user_data)

    product = Product(
        name="Coffee Beans",
        price=Decimal(price),
        stock=10,
        is_active=True,
    )
    test_db.add(product)
    test_db.flush()

    res = auth_client.post(
        "/orders",
        json={"items": [{"product_id": product.id, "quantity": 1}]},
    )
    assert res.status_code == 200
    return auth_client, res.json()["id"], product


def _full_flow_to_receipt(auth_client, order_id):
    """happy path：intent → mock-provider → receipt。回傳 receipt 字串。"""
    intent = auth_client.post(f"/orders/{order_id}/payment-intent")
    assert intent.status_code == 200
    token = intent.json()["token"]

    provider = auth_client.post("/mock-provider/pay", json={"token": token})
    assert provider.status_code == 200
    return provider.json()["receipt"]


def test_payment_happy_path(
    test_db, create_test_user, test_user_data, session_auth_client
):
    auth_client, order_id, _product = _signup_and_create_order(
        test_db, create_test_user, test_user_data, session_auth_client
    )

    receipt = _full_flow_to_receipt(auth_client, order_id)

    pay = auth_client.post(f"/orders/{order_id}/pay", json={"receipt": receipt})
    assert pay.status_code == 200
    assert pay.json()["order"]["status"] == "paid"

    # intent 被消耗（nonce 單次使用的 DB 憑據）。
    intent = test_db.scalar(select(PaymentIntent))
    test_db.refresh(intent)
    assert intent.status == "consumed"
    assert intent.used_at is not None


def test_receipt_replay_rejected(
    test_db, create_test_user, test_user_data, session_auth_client
):
    # 同一張收據只能用一次——重放攻擊被 nonce 的 DB 憑據擋下。
    auth_client, order_id, _ = _signup_and_create_order(
        test_db, create_test_user, test_user_data, session_auth_client
    )
    receipt = _full_flow_to_receipt(auth_client, order_id)

    first = auth_client.post(f"/orders/{order_id}/pay", json={"receipt": receipt})
    assert first.status_code == 200

    # 這個 user 再建一筆新訂單，拿同一張收據付款。
    from app.models import Product

    product = Product(name="Tea", price=Decimal("5.00"), stock=10, is_active=True)
    test_db.add(product)
    test_db.flush()
    second = auth_client.post(
        "/orders", json={"items": [{"product_id": product.id, "quantity": 1}]}
    )
    second_order_id = second.json()["id"]

    replay = auth_client.post(
        f"/orders/{second_order_id}/pay", json={"receipt": receipt}
    )
    assert replay.status_code in (400, 409)


def test_tampered_token_rejected(
    test_db, create_test_user, test_user_data, session_auth_client
):
    # intent token 的 payload 被竄改（例如改金額）→ 驗章失敗。
    auth_client, order_id, _ = _signup_and_create_order(
        test_db, create_test_user, test_user_data, session_auth_client
    )

    intent = auth_client.post(f"/orders/{order_id}/payment-intent")
    token = intent.json()["token"]

    # 竄改：把 token 的 body 換成「金額 0.01」的同構 payload（簽章不可能對）。
    import base64
    import json

    body, sig = token.rsplit(".", 1)
    payload = json.loads(base64.urlsafe_b64decode(body + "=="))
    payload["amount"] = "0.01"
    tampered_body = (
        base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    )
    tampered = f"{tampered_body}.{sig}"

    provider = auth_client.post("/mock-provider/pay", json={"token": tampered})
    assert provider.status_code == 400


def test_intent_token_cannot_be_used_as_receipt(
    test_db, create_test_user, test_user_data, session_auth_client
):
    # kind 隔離：intent token 直接拿去當 receipt → 拒絕（混淆攻擊）。
    auth_client, order_id, _ = _signup_and_create_order(
        test_db, create_test_user, test_user_data, session_auth_client
    )

    intent = auth_client.post(f"/orders/{order_id}/payment-intent")
    token = intent.json()["token"]

    pay = auth_client.post(f"/orders/{order_id}/pay", json={"receipt": token})
    assert pay.status_code == 400


def test_receipt_bound_to_order(
    test_db, create_test_user, test_user_data, session_auth_client
):
    # 拿 A 訂單的收據付 B 訂單 → 綁定檢查拒絕。
    from app.models import Product

    auth_client, order_a, _ = _signup_and_create_order(
        test_db, create_test_user, test_user_data, session_auth_client
    )
    receipt = _full_flow_to_receipt(auth_client, order_a)

    product = Product(name="Tea", price=Decimal("5.00"), stock=10, is_active=True)
    test_db.add(product)
    test_db.flush()
    order_b = auth_client.post(
        "/orders", json={"items": [{"product_id": product.id, "quantity": 1}]}
    ).json()["id"]

    pay = auth_client.post(f"/orders/{order_b}/pay", json={"receipt": receipt})
    assert pay.status_code == 400


def test_payment_intent_requires_ownership(
    test_db, create_test_user, test_user_data, session_auth_client
):
    # A 建單，B 拿 A 的訂單 id 要 intent → 404（不洩漏存在性）。
    _, order_id, _ = _signup_and_create_order(
        test_db, create_test_user, test_user_data, session_auth_client
    )

    attacker_data = {
        "name": "Attacker",
        "email": f"attacker-{test_user_data['email']}",
        "password": "AttackerPass123",
    }
    create_test_user(**attacker_data)
    attacker_client = session_auth_client(attacker_data)

    res = attacker_client.post(f"/orders/{order_id}/payment-intent")
    assert res.status_code == 404


def test_new_intent_invalidates_old_token(
    test_db, create_test_user, test_user_data, session_auth_client
):
    # 一筆訂單同時只有一個有效 intent：重新要 intent 後，舊 token 被作廢。
    auth_client, order_id, _ = _signup_and_create_order(
        test_db, create_test_user, test_user_data, session_auth_client
    )

    old_token = auth_client.post(f"/orders/{order_id}/payment-intent").json()["token"]
    new_token = auth_client.post(f"/orders/{order_id}/payment-intent").json()["token"]

    # 舊 token 在 provider 端已被作廢。
    old_provider = auth_client.post("/mock-provider/pay", json={"token": old_token})
    assert old_provider.status_code == 409

    # 新 token 仍可正常走完流程。
    receipt = auth_client.post("/mock-provider/pay", json={"token": new_token}).json()[
        "receipt"
    ]
    pay = auth_client.post(f"/orders/{order_id}/pay", json={"receipt": receipt})
    assert pay.status_code == 200


def test_expired_intent_rejected(
    test_db, create_test_user, test_user_data, session_auth_client, monkeypatch
):
    # token 的 exp 簽在 payload 裡——把 TTL 簽成 0 秒模擬「過期後才兌換」。
    from app.core import payment as payment_mod

    auth_client, order_id, _ = _signup_and_create_order(
        test_db, create_test_user, test_user_data, session_auth_client
    )

    intent = auth_client.post(f"/orders/{order_id}/payment-intent").json()
    # 用同一個 secret 簽一張「已過期」的 token（exp 在過去）。
    expired = payment_mod._pack(
        {
            "intent_id": 1,
            "nonce": "expired-nonce",
            "order_id": order_id,
            "amount": "19.99",
        },
        ttl=-10,
        kind="intent",
    )
    assert expired != intent["token"]

    provider = auth_client.post("/mock-provider/pay", json={"token": expired})
    assert provider.status_code == 400
