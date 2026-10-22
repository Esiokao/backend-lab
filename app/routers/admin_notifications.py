from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database import get_db
from app.models import NotificationBroadcast, NotificationOutbox, User
from app.schemas.AdminNotification import AdminNotificationCreate
from app.schemas.Notification import NotificationBroadcastCreate

router = APIRouter(
    prefix="/admin/notifications",
    tags=["Admin Notifications"],
)


@router.post("/", status_code=status.HTTP_202_ACCEPTED)
def create_admin_notification(
    payload: AdminNotificationCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    user = db.get(User, payload.user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    event = NotificationOutbox(
        event_type="notifications.admin_created",
        payload={
            "user_id": payload.user_id,
            "title": payload.title,
            "body": payload.body,
        },
    )

    db.add(event)
    db.commit()
    db.refresh(event)

    return {
        "outbox_event_id": event.id,
        "status": event.status,
    }


@router.post("/broadcasts", status_code=status.HTTP_201_CREATED)
def create_notification_broadcast(
    payload: NotificationBroadcastCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    broadcast = NotificationBroadcast(
        type=payload.type,
        title=payload.title,
        body=payload.body,
    )

    db.add(broadcast)
    db.commit()
    db.refresh(broadcast)

    return broadcast
