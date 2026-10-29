import logging

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.core.events import BROADCAST_CHANNEL, EventType
from app.core.redis import redis_client
from app.core.request_size import SizeLimitedAPIRouter
from app.database import get_db
from app.models import NotificationBroadcast, NotificationOutbox, User
from app.schemas.AdminNotification import AdminNotificationCreate
from app.schemas.Notification import NotificationBroadcastCreate

logger = logging.getLogger(__name__)

router = SizeLimitedAPIRouter(
    prefix="/admin/notifications",
    tags=["Admin Notifications"],
)


# 定向通知
@router.post("", status_code=status.HTTP_202_ACCEPTED)
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
        event_type=EventType.admin_notification_created,
        payload={
            "type": "admin_announcement",
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


# worker不參與, 純用一張獨立的表來做廣播通知, 讓管理員可以直接新增廣播訊息
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

    # 公告是全體廣播：對公告頻道喊一聲，所有連著 SSE 的瀏覽器即時刷新。
    # 失敗不影響公告本身（已落庫），輪詢會兜底。
    try:
        redis_client.publish(BROADCAST_CHANNEL, "refresh")
    except Exception:
        logger.warning(
            "Broadcast SSE publish failed (poller will catch up)", exc_info=True
        )

    return broadcast


# 刪特定id的廣播通知, 讓admin可以刪除廣播訊息
@router.delete("/broadcasts/{broadcast_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_notification_broadcast(
    broadcast_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    broadcast = db.get(NotificationBroadcast, broadcast_id)

    if broadcast is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification broadcast not found",
        )

    # 204 無回應 body，與 DELETE /admin/orders/{id} 慣例一致。
    db.delete(broadcast)
    db.commit()
