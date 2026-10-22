from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class NotificationResponse(BaseModel):
    # 定義單筆通知對外公開的欄位。
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    body: str
    data: dict[str, Any]
    created_at: datetime
    read_at: datetime | None


class NotificationListResponse(BaseModel):
    # 統一列表格式，讓前端取得下一頁游標。
    items: list[NotificationResponse]
    next_cursor: str | None


class AdminNotificationJobPayload(BaseModel):
    outbox_event_id: int = Field(gt=0)
    user_id: int = Field(gt=0)
    type: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=2000)


class NotificationBroadcastCreate(BaseModel):
    """廣播通知"""

    type: str = Field(
        default="admin_announcement",
        min_length=1,
        max_length=100,
    )
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=2000)
