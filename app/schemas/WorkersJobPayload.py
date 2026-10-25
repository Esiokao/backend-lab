from pydantic import BaseModel, Field


class OutboxJobPayload(BaseModel):
    """所有 outbox 任務 payload 的共同欄位。"""

    outbox_event_id: int = Field(gt=0)


class ProductRestockJobPayload(OutboxJobPayload):
    product_id: int = Field(gt=0)


class AdminNotificationJobPayload(OutboxJobPayload):
    outbox_event_id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    type: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=2000)


class OrderPaidJobPayload(OutboxJobPayload):
    order_id: int = Field(gt=0)


class OrderCompletedJobPayload(OutboxJobPayload):
    order_id: int = Field(gt=0)


class OrderCreatedJobPayload(OutboxJobPayload):
    order_id: int = Field(gt=0)


class OrderCancelledJobPayload(OutboxJobPayload):
    order_id: int = Field(gt=0)
