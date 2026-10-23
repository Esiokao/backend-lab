from fastapi import APIRouter, Depends
from sqlalchemy import select
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
    }
