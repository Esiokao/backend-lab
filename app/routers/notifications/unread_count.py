from sqlalchemy import func, select

from app.core.dependencies import CurrentUser
from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Notification, NotificationBroadcast

router = SizeLimitedAPIRouter(prefix="/notifications")


@router.get("/unread-count")
def get_unread_notification_count(
    current_user: CurrentUser,
    session: DbSession,
):
    # 只計算目前登入使用者尚未讀取的通知。
    stmt = (
        select(func.count())
        .select_from(Notification)
        .where(
            Notification.user_id == current_user.id,
            Notification.read_at.is_(None),
        )
    )

    unread_count = session.execute(stmt).scalar_one()

    # 廣播未讀採同一水位規則（v1.12），讓鈴鐺徽章能合計兩種未讀。
    watermark = current_user.last_seen_broadcast_id or 0
    broadcasts_unread = (
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
        "unread_count": unread_count,
        "broadcasts_unread": broadcasts_unread,
    }
