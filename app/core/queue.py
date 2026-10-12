from app.core.rq_publisher import RQPublisher
from app.core.task_publisher import TaskPublisher


def get_task_publisher() -> TaskPublisher:
    """提供背景任務發布器。

    回傳型別宣告為 TaskPublisher（抽象），
    讓業務程式碼只依賴 Protocol，不認識 RQ。
    之後要換 RabbitMQ，只需要改這裡的回傳值。
    """

    # 每次請求建立新的 publisher；RQPublisher 本身是輕量物件，
    # 底層的 Redis 連線由 rq_redis 共享。
    return RQPublisher()
