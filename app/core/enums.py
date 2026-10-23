"""訂單與通知的領域列舉：狀態機的唯一真相來源。"""

from enum import Enum


class OrderStatus(str, Enum):
    """訂單狀態（繼承 str：DB 存字串、JSON 序列化直接是字串）。"""

    created = "created"  # 已建立，未付款
    pending = "pending"  # 已付款，待出貨
    processing = "processing"  # 出貨處理中
    completed = "completed"  # 已送達／完成（終態）
    cancelled = "cancelled"  # 已取消（終態）


# 合法的狀態轉移（狀態機）：key = 現狀，value = 允許的下一個狀態。
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.created: {OrderStatus.pending, OrderStatus.cancelled},
    OrderStatus.pending: {OrderStatus.processing, OrderStatus.cancelled},
    OrderStatus.processing: {OrderStatus.completed, OrderStatus.cancelled},
    OrderStatus.completed: set(),
    OrderStatus.cancelled: set(),
}
