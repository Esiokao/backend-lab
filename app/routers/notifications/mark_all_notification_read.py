# app/routers/notifications/mark_all_notification_read.py

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import Notification, User

router = APIRouter(prefix="/notifications")


@router.patch("/mark_all_read")
def mark_all_notification_read(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    stmt = select(Notification).where(
        Notification.user_id == current_user.id,
        Notification.read_at.is_(None),
    )

    notifications = session.execute(stmt).scalars().all()

    now = datetime.now(timezone.utc)

    for notification in notifications:
        notification.read_at = now

    session.commit()

    return {
        "updated_count": len(notifications),
    }
