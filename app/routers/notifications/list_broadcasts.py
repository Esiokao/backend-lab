from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import NotificationBroadcast, User

router = APIRouter(prefix="/notifications")


@router.get("/broadcasts")
def list_notification_broadcasts(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
):
    stmt = select(NotificationBroadcast).order_by(
        NotificationBroadcast.created_at.desc(),
        NotificationBroadcast.id.desc(),
    )

    broadcasts = session.scalars(stmt).all()

    # 廣播未讀（v1.12 水位法）：id 超過水位、且不是使用者註冊前發布的。
    watermark = current_user.last_seen_broadcast_id or 0
    unread_count = (
        session.execute(
            select(func.count())
            .select_from(NotificationBroadcast)
            .where(
                NotificationBroadcast.id > watermark,
                NotificationBroadcast.created_at > current_user.created_at,
            )
        ).scalar_one()
        if current_user.created_at is not None
        else 0
    )

    return {
        "items": [
            {
                "id": broadcast.id,
                "type": broadcast.type,
                "title": broadcast.title,
                "body": broadcast.body,
                "created_at": broadcast.created_at,
            }
            for broadcast in broadcasts
        ],
        "unread_count": unread_count,
    }
