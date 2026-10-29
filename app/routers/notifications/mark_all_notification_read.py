# app/routers/notifications/mark_all_notification_read.py

from datetime import datetime, timezone

from sqlalchemy import select

from app.core.dependencies import CurrentUser
from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Notification

router = SizeLimitedAPIRouter(prefix="/notifications")


@router.patch("/mark_all_read")
def mark_all_notification_read(
    current_user: CurrentUser,
    session: DbSession,
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
