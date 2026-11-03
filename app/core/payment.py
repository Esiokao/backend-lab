# app/core/payment.py
#
# 付款憑證的 HMAC 簽章工具：intent token 與 receipt 的生成與驗證。
#
# 安全屬性：
#   - 簽章（HMAC-SHA256，PAYMENT_SECRET）→ payload 不可竄改（金額、訂單綁定）
#   - exp 簽進 payload                    → 過期即失效（重放窗口有限）
#   - kind 欄位                           → intent token 不能當 receipt 用（混淆攻擊）
#   - nonce 單次使用                      → 由 DB（payment_intents.used_at）保證，
#                                           簽章工具本身不負責狀態

import base64
import hashlib
import hmac
import json
import os
import time

PAYMENT_SECRET = os.getenv("PAYMENT_SECRET", "dev-payment-secret-do-not-use-in-prod")

# intent token 的有效時間：超過後 mock-provider 拒絕兌換。
PAYMENT_INTENT_TTL_SECONDS = int(os.getenv("PAYMENT_INTENT_TTL_SECONDS", "300"))

# receipt 的有效時間：付款端點驗章的額外窗口（provider 兌換後要盡快 settle）。
RECEIPT_TTL_SECONDS = int(os.getenv("RECEIPT_TTL_SECONDS", "300"))


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _sign(body: str) -> str:
    return hmac.new(PAYMENT_SECRET.encode(), body.encode(), hashlib.sha256).hexdigest()


def _pack(payload: dict, ttl: int, kind: str) -> str:
    """payload + kind + exp → 簽章 token（body.sig）。"""
    full = {
        **payload,
        "kind": kind,
        "exp": int(time.time()) + ttl,
    }
    body = _b64url(json.dumps(full, sort_keys=True).encode())
    return f"{body}.{_sign(body)}"


def _unpack(token: str, kind: str) -> dict | None:
    """驗章 + 驗 kind + 驗 exp。任何一步失敗回 None（不區分原因，避免洩漏資訊）。"""
    try:
        body, sig = token.rsplit(".", 1)
        if not hmac.compare_digest(_sign(body), sig):
            return None
        payload = json.loads(base64.urlsafe_b64decode(body + "=="))
        if payload.get("kind") != kind:
            return None
        if int(payload.get("exp", 0)) < time.time():
            return None
        return payload
    except (ValueError, TypeError, KeyError):
        # json/base64/int 的各種失敗形式都是這三類的子類——
        # 驗章失敗一律回 None，不洩漏失敗原因。
        return None


def issue_intent_token(payload: dict) -> str:
    """簽發 intent token（kind=intent）。payload 需含 intent_id / nonce / order_id / amount。"""
    return _pack(payload, PAYMENT_INTENT_TTL_SECONDS, "intent")


def verify_intent_token(token: str) -> dict | None:
    return _unpack(token, "intent")


def issue_receipt(payload: dict) -> str:
    """簽發 receipt（kind=receipt）。payload 需含 nonce / order_id / amount。"""
    return _pack(payload, RECEIPT_TTL_SECONDS, "receipt")


def verify_receipt(receipt: str) -> dict | None:
    return _unpack(receipt, "receipt")
