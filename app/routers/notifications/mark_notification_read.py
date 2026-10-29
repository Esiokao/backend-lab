# app/routers/notifications/mark_notification_read.py

from datetime import datetime, timezone

from fastapi import Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.request_size import SizeLimitedAPIRouter
from app.database import get_db
from app.models import Notification, User

router = SizeLimitedAPIRouter(prefix="/notifications")


@router.patch("/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    # 查詢時同時限制通知 ID 與擁有者，避免跨使用者存取。
    stmt = select(Notification).where(
        Notification.id == notification_id,
        Notification.user_id == current_user.id,
    )
    notification = session.execute(stmt).scalar_one_or_none()

    if notification is None:
        raise HTTPException(
            status_code=404,
            detail="Notification not found",
        )

    # 重複請求不覆寫第一次的已讀時間。
    if notification.read_at is None:
        notification.read_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(notification)

    return {
        "id": notification.id,
        "read_at": notification.read_at,
    }
