import base64
import json
from datetime import datetime

from fastapi import HTTPException, Query
from sqlalchemy import and_, or_, select

from app.core.dependencies import CurrentUser
from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Notification
from app.schemas.Notification import (
    NotificationListResponse,
    NotificationResponse,
)

router = SizeLimitedAPIRouter(prefix="/notifications")


def encode_cursor(notification: Notification) -> str:
    # 將排序欄位編碼成下一頁的游標。
    payload = {
        "created_at": notification.created_at.isoformat(),
        "id": notification.id,
    }
    raw = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str) -> tuple[datetime, int]:
    # 解碼並驗證游標格式。
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.b64decode(
            padded,
            altchars=b"-_",
            validate=True,
        )
        payload = json.loads(raw)

        created_at = datetime.fromisoformat(payload["created_at"])
        notification_id = payload["id"]

        if (
            created_at.tzinfo is None
            or not isinstance(notification_id, int)
            or isinstance(notification_id, bool)
            or notification_id <= 0
        ):
            raise ValueError("Invalid cursor values")

        return created_at, notification_id

    except (ValueError, TypeError, KeyError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Invalid cursor",
        ) from exc


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    current_user: CurrentUser,
    db: DbSession,
    limit: int = Query(default=20, ge=1, le=100),
    cursor: str | None = Query(default=None),
):
    # 每次查詢都限制在目前登入者的通知範圍內。
    stmt = select(Notification).where(Notification.user_id == current_user.id)

    if cursor is not None:
        cursor_created_at, cursor_id = decode_cursor(cursor)

        # 按照 created_at、id 的降冪排序，查詢游標之後的資料。
        stmt = stmt.where(
            or_(
                Notification.created_at < cursor_created_at,
                and_(
                    Notification.created_at == cursor_created_at,
                    Notification.id < cursor_id,
                ),
            )
        )

    # 多查一筆，判斷是否還有下一頁。
    stmt = stmt.order_by(
        Notification.created_at.desc(),
        Notification.id.desc(),
    ).limit(limit + 1)

    notifications = db.execute(stmt).scalars().all()
    has_more = len(notifications) > limit
    items = notifications[:limit]

    next_cursor = encode_cursor(items[-1]) if has_more else None

    return NotificationListResponse(
        items=[NotificationResponse.model_validate(item) for item in items],
        next_cursor=next_cursor,
    )
