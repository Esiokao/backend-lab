from sqlalchemy import select

from app.core.dependencies import CurrentUser
from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import NotificationBroadcast

router = SizeLimitedAPIRouter(prefix="/notifications")


@router.post("/broadcasts/read-all")
def mark_all_broadcasts_read(
    current_user: CurrentUser,
    session: DbSession,
):
    # 廣播已讀水位（v1.12）：推到最新一則的 id（全有全無）。
    latest_id = session.execute(
        select(NotificationBroadcast.id)
        .order_by(NotificationBroadcast.id.desc())
        .limit(1)
    ).scalar_one_or_none()

    current_user.last_seen_broadcast_id = latest_id or 0
    session.commit()

    return {"broadcasts_unread": 0}
