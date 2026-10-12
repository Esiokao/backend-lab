from typing import Protocol


class TaskPublisher(Protocol):
    """定義背景任務發布器必須提供的介面。"""

    def enqueue(
        self,
        task_name: str,
        payload: dict[str, object],
    ) -> str:
        """發布任務並回傳任務 ID。

        payload 必須只包含可序列化的任務資料，
        例如訂單 ID，而不是 SQLAlchemy ORM 物件。
        """
        ...
