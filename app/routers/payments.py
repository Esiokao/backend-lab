# app/routers/payments.py
# 付款三步流程的前兩步：intent 簽發與 mock-provider 收據兌換。
#
# 角色邊界（對應真實世界的分工）：
#   /orders/{id}/payment-intent = 商家後端：向供應商註冊交易（金額由後端計算並簽進 token）
#   /mock-provider/pay          = 模擬金流供應商：收錢 + 簽發收據（HMAC）
#   orders.py 的 /orders/{id}/pay = 商家後端：驗收據才轉 paid
# 沒有收據，任何人都無法把訂單標成 paid——付款邊界由收據簽章構成。

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select, update

from app.core.dependencies import CurrentUser
from app.core.enums import OrderStatus
from app.core.payment import (
    PAYMENT_INTENT_TTL_SECONDS,
    issue_intent_token,
    issue_receipt,
    verify_intent_token,
    verify_receipt,
)
from app.database import DbSession
from app.models import Order, OrderItem, PaymentIntent
from app.schemas.Payment import (
    MockProviderPay,
    MockProviderReceipt,
    PaymentIntentResponse,
)

router = APIRouter(tags=["Payments"])


def _get_own_unpaid_order(session, order_id: int, current_user) -> Order:
    """owner only + 必須是未付款狀態——intent 與 pay 端點共用的守門。"""
    stmt = select(Order).where(
        Order.id == order_id,
        Order.user_id == current_user.id,
    )
    order = session.execute(stmt).scalar_one_or_none()

    if order is None:
        raise HTTPException(status_code=404, detail="Order not found")

    if order.status != OrderStatus.unpaid.value:
        raise HTTPException(
            status_code=400,
            detail=f"Order cannot be paid in its current status: {order.status}",
        )

    return order


def _order_amount(session, order_id: int):
    """金額一律由後端從訂單明細計算——client 沒有任何機會報價。"""
    items = (
        session.execute(select(OrderItem).where(OrderItem.order_id == order_id))
        .scalars()
        .all()
    )

    if not items:
        raise HTTPException(status_code=400, detail="Order has no items")

    return sum(item.unit_price * item.quantity for item in items)


@router.post("/orders/{order_id}/payment-intent", response_model=PaymentIntentResponse)
def create_payment_intent(
    order_id: int,
    current_user: CurrentUser,
    session: DbSession,
):
    """向「供應商」註冊交易：金額後端計算、簽進 token、5 分鐘時效、單一有效 intent。"""
    order = _get_own_unpaid_order(session, order_id, current_user)
    amount = _order_amount(session, order.id)

    # 舊 intent 全部作廢：一筆訂單同時只有一個可兌換的 token。
    session.execute(
        update(PaymentIntent)
        .where(
            PaymentIntent.order_id == order.id,
            PaymentIntent.status == "pending",
        )
        .values(status="cancelled")
    )

    nonce = secrets.token_urlsafe(16)
    intent = PaymentIntent(
        order_id=order.id,
        nonce=nonce,
        amount=amount,
        status="pending",
        expires_at=datetime.now(timezone.utc)
        + timedelta(seconds=PAYMENT_INTENT_TTL_SECONDS),
    )
    session.add(intent)
    session.commit()
    session.refresh(intent)

    token = issue_intent_token(
        {
            "intent_id": intent.id,
            "nonce": intent.nonce,
            "order_id": order.id,
            "amount": str(intent.amount),
        }
    )

    return {
        "token": token,
        "amount": str(intent.amount),
        "expires_in": PAYMENT_INTENT_TTL_SECONDS,
    }


@router.post("/mock-provider/pay", response_model=MockProviderReceipt)
def mock_provider_pay(data: MockProviderPay, session: DbSession):
    """模擬金流供應商：驗 token（簽章/時效）→ 收錢 → 簽發收據。

    不要求我們的 session——供應商是外部系統，token 本身就是它的憑證。
    """
    payload = verify_intent_token(data.token)

    if payload is None:
        raise HTTPException(status_code=400, detail="Invalid or expired payment token")

    intent = session.execute(
        select(PaymentIntent).where(PaymentIntent.nonce == payload["nonce"])
    ).scalar_one_or_none()

    if intent is None or intent.status != "pending":
        raise HTTPException(
            status_code=409, detail="Payment intent is no longer available"
        )

    if intent.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Payment intent expired")

    # 供應商「收到錢」：intent 標記 completed（此時還沒動訂單——收據未兌換）。
    intent.status = "completed"
    session.commit()

    receipt = issue_receipt(
        {
            "nonce": intent.nonce,
            "order_id": intent.order_id,
            "amount": str(intent.amount),
        }
    )

    return {"receipt": receipt}


def settle_receipt(session, order, receipt: str):
    """驗收據 + 消耗 intent nonce。由 orders.pay_order 在同一交易內呼叫。

    任何一步失敗都 raise（400/409），呼叫端 rollback——intent 與訂單同生共死。
    """
    payload = verify_receipt(receipt)

    if payload is None:
        raise HTTPException(status_code=400, detail="Invalid payment receipt")

    intent = session.execute(
        select(PaymentIntent).where(PaymentIntent.nonce == payload["nonce"])
    ).scalar_one_or_none()

    if intent is None:
        raise HTTPException(status_code=400, detail="Unknown payment receipt")

    # 收據綁定：拿 A 訂單的收據付 B 訂單 → 拒絕。
    if intent.order_id != order.id:
        raise HTTPException(
            status_code=400, detail="Receipt does not belong to this order"
        )

    # 供應商必須已確認收款（pending = 沒兌換過；consumed = 收據已用過）。
    if intent.status == "consumed":
        raise HTTPException(status_code=409, detail="Receipt already used")
    if intent.status != "completed":
        raise HTTPException(status_code=400, detail="Payment not confirmed by provider")

    # 過期防線（provider 兌換時查過一次，這裡是第二道）。
    if intent.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Payment intent expired")

    # 單次使用：消耗 nonce（receipt 重放在此被 DB 憑據擋下）。
    intent.status = "consumed"
    intent.used_at = func.now()

    return intent.amount
