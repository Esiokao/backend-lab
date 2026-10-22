from pydantic import BaseModel, Field


class AdminNotificationCreate(BaseModel):
    user_id: int = Field(gt=0)
    title: str = Field(min_length=1, max_length=255)
    body: str = Field(min_length=1, max_length=2000)
