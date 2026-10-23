import os

import redis
from rq import Queue

from app.core.events import EventType

# RQ 使用獨立的 Redis 連線，不影響 Rate Limiting。
rq_redis = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", "6379")),
)

NOTIFICATION_QUEUE_NAME = "notifications"

default_queue = Queue(
    NOTIFICATION_QUEUE_NAME,
    connection=rq_redis,
)

TASK_REGISTRY: dict[EventType, str] = {
    EventType.order_created: ("app.workers.notifications.notify_order_created"),
    EventType.admin_notification_created: (
        "app.workers.notifications.notify_admin_notification"
    ),
    EventType.product_restocked: ("app.workers.notifications.notify_product_restocked"),
    EventType.order_paid: ("app.workers.notifications.notify_order_paid"),
}


class RQPublisher:
    """使用 RQ 實作背景任務發布介面。"""

    def __init__(self, queue: Queue = default_queue) -> None:
        self.queue = queue

    def enqueue(
        self,
        task_name: str,
        payload: dict[str, object],
    ) -> str:
        # 拒絕未註冊的任務名稱。
        task_path = TASK_REGISTRY.get(task_name)
        if task_path is None:
            raise ValueError(f"Unknown task: {task_name}")

        # 將任務交給 RQ；Worker 之後才會執行。
        job = self.queue.enqueue(
            task_path,
            kwargs={"payload": payload},
        )

        return job.id
