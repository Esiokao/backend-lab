from pydantic import BaseModel, Field


class ProductRestockJobPayload(BaseModel):
    outbox_event_id: int = Field(gt=0)
    product_id: int = Field(gt=0)


class AdminNotificationJobPayload(BaseModel):
    outbox_event_id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    type: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=2000)


class OrderPaidJobPayload(BaseModel):
    outbox_event_id: int = Field(gt=0)
    order_id: int = Field(gt=0)


class OrderCompletedJobPayload(BaseModel):
    outbox_event_id: int = Field(gt=0)
    order_id: int = Field(gt=0)


class OrderCreatedJobPayload(BaseModel):
    outbox_event_id: int = Field(gt=0)
    order_id: int = Field(gt=0)


class OrderCancelledJobPayload(BaseModel):
    outbox_event_id: int = Field(gt=0)
    order_id: int = Field(gt=0)
