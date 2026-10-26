"""模擬倉儲履約：把已付款訂單依時間自動推進狀態機。

真實世界裡 pending（已付款）→ processing（出貨處理中）→ completed（送達）
是倉儲在做的事；本模組用時間延遲模擬這段旅程，讓訂單不必靠 admin 手動
改狀態也能走到終態。completed 與 NotificationOutbox 在同一交易寫入，
因此「訂單已完成」通知走既有 outbox → dispatcher → worker 鏈路自動發出。
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.events import EventType
from app.database import SessionLocal
from app.models import NotificationOutbox, Order

logger = logging.getLogger(__name__)

# 付款後 N 秒進入 processing；自付款起算 M 秒標記 completed
# （涵蓋 processing 停留時間，預設 5 + 60 = 65 秒）。
PROCESSING_DELAY_SECONDS = int(os.getenv("FULFILLMENT_PROCESSING_DELAY_SECONDS", "5"))
COMPLETION_DELAY_SECONDS = int(os.getenv("FULFILLMENT_COMPLETION_DELAY_SECONDS", "65"))

POLL_INTERVAL_SECONDS = 5
BATCH_SIZE = 100


def _claim_batch(
    session: Session, statuses: list[str], cutoff: datetime
) -> list[Order]:
    """撈出到期且鎖得走的訂單（skip_locked，多實體安全）。"""
    stmt = (
        select(Order)
        .where(
            Order.status.in_(statuses),
            Order.paid_at.is_not(None),
            Order.paid_at <= cutoff,
        )
        .order_by(Order.id.asc())
        .limit(BATCH_SIZE)
        .with_for_update(skip_locked=True)
    )
    return list(session.execute(stmt).scalars().all())


def advance_once(session: Session, *, now: datetime | None = None) -> int:
    """推進一批到期訂單，回傳本輪狀態被推進的訂單數。"""
    now = now or datetime.now(timezone.utc)
    advanced = 0

    # 1) 已付款且到期 → processing（模擬倉儲撿貨）。
    orders = _claim_batch(
        session,
        ["pending"],
        now - timedelta(seconds=PROCESSING_DELAY_SECONDS),
    )
    for order in orders:
        order.status = "processing"
        advanced += 1
    session.commit()

    # 2) processing 且到期 → completed；同一交易寫 outbox 事件發通知。
    orders = _claim_batch(
        session,
        ["processing"],
        now - timedelta(seconds=COMPLETION_DELAY_SECONDS),
    )
    for order in orders:
        order.status = "completed"
        session.add(
            NotificationOutbox(
                event_type=EventType.order_completed,
                payload={"order_id": order.id},
            )
        )
        advanced += 1
    session.commit()

    return advanced


def run_fulfillment_worker() -> None:
    """持續輪詢訂單狀態；短暫失敗不會終止整個 Worker。"""
    while True:
        try:
            with SessionLocal() as session:
                advanced = advance_once(session)
                if advanced:
                    logger.info("Fulfillment advanced %s orders", advanced)
        except Exception:
            logger.exception("Fulfillment worker iteration failed")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_fulfillment_worker()
