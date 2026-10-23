from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import Notification, User

router = APIRouter(prefix="/notifications")


@router.get("/unread-count")
def get_unread_notification_count(
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
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

    return {"unread_count": unread_count}
