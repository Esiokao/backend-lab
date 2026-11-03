from sqlalchemy import func, select

from app.core.dependencies import CurrentUser
from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import NotificationBroadcast

router = SizeLimitedAPIRouter(prefix="/notifications")


@router.get("/broadcasts")
def list_notification_broadcasts(
    current_user: CurrentUser,
    session: DbSession,
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
