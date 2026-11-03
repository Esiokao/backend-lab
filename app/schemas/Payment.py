# app/schemas/Payment.py
# 付款三步流程的請求/回應契約。

from pydantic import BaseModel


class PaymentIntentResponse(BaseModel):
    """payment-intent 的回應：token 拿去 mock-provider 兌換收據。"""

    token: str
    amount: str  # Decimal 序列化為字串（與 ProductResponse 的價格慣例一致）
    expires_in: int  # token 有效秒數


class MockProviderPay(BaseModel):
    token: str


class MockProviderReceipt(BaseModel):
    receipt: str


class PayWithReceipt(BaseModel):
    """pay 端點的唯一付款憑證：mock-provider 簽發的收據。"""

    receipt: str
