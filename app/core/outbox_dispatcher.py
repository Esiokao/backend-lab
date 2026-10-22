import logging
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.core.queue import get_task_publisher
from app.core.task_publisher import TaskPublisher
from app.database import SessionLocal
from app.models import NotificationOutbox

logger = logging.getLogger(__name__)

BATCH_SIZE = 100
POLL_INTERVAL_SECONDS = 5
VISIBILITY_TIMEOUT_SECONDS = 300
MAX_RETRY_DELAY_SECONDS = 300


def dispatch_once(
    session: Session, batch_size: int = BATCH_SIZE, *, publisher: TaskPublisher
) -> int:
    """批次發布待處理事件，回傳本輪嘗試處理的事件數。"""
    now = datetime.now(timezone.utc)

    # 同時處理新事件，以及已發布但逾時未完成的事件。
    stmt = (
        select(NotificationOutbox)
        .where(
            or_(
                and_(
                    NotificationOutbox.status == "pending",
                    NotificationOutbox.available_at <= now,
                ),
                and_(
                    NotificationOutbox.status == "dispatched",
                    NotificationOutbox.processed_at.is_(None),
                    NotificationOutbox.available_at <= now,
                ),
            )
        )
        .order_by(NotificationOutbox.id.asc())
        .limit(batch_size)
        .with_for_update(skip_locked=True)
    )

    events = session.execute(stmt).scalars().all()
    if not events:
        return 0

    for event in events:
        # 使用獨立 payload，避免修改 ORM 物件中的 JSON。
        payload = dict(event.payload)
        payload["outbox_event_id"] = event.id

        # 每次發布嘗試都計數，包括失敗的情況。
        event.attempts += 1

        try:
            publisher.enqueue(event.event_type, payload)

            # dispatched 代表已交給佇列，不代表通知已完成。
            event.status = "dispatched"
            event.dispatched_at = now
            event.available_at = now + timedelta(seconds=VISIBILITY_TIMEOUT_SECONDS)
            event.last_error = None

        except Exception as exc:
            # Redis 故障時保留事件，之後再重試。
            event.status = "pending"
            retry_delay = min(
                2 ** min(event.attempts, 8),
                MAX_RETRY_DELAY_SECONDS,
            )
            event.available_at = now + timedelta(seconds=retry_delay)
            event.last_error = str(exc)[:2000]

            logger.exception(
                "Failed to dispatch outbox event id=%s",
                event.id,
            )

    # 一批事件只在這裡提交一次，減少逐筆 commit 的成本。
    session.commit()
    return len(events)


def run_dispatcher() -> None:
    """持續輪詢 Outbox；短暫失敗不會終止整個 Dispatcher。"""
    publisher = get_task_publisher()
    while True:
        try:
            with SessionLocal() as session:
                dispatch_once(session, publisher=publisher)
        except Exception:
            logger.exception("Outbox dispatcher iteration failed")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_dispatcher()
