"""訂單與通知的領域列舉：狀態機的唯一真相來源。"""

from enum import Enum


class OrderStatus(str, Enum):
    """訂單狀態（繼承 str：DB 存字串、JSON 序列化直接是字串）。"""

    created = "created"  # 已建立，未付款
    pending = "pending"  # 已付款，待出貨
    processing = "processing"  # 出貨處理中
    completed = "completed"  # 已送達／完成（終態）
    cancelled = "cancelled"  # 已取消（終態）


class NotificationType(str, Enum):
    """站內通知的種類（鈴鐺面板的分類依據）。"""

    admin_announcement = "admin_announcement"  # admin 公告
    order_created = "order_created"  # 訂單建立通知
    product_restocked = "product_restocked"  # 到貨通知
    order_paid = "order_paid"  # 訂單付款通知
    order_completed = "order_completed"  # 訂單完成通知
    order_cancelled = "order_cancelled"  # 訂單取消通知


# 合法的狀態轉移（狀態機）：key = 現狀，value = 允許的下一個狀態。
# pending -> completed 與 POST /orders/{id}/complete 一致（v1.18 快速完成）。
ALLOWED_TRANSITIONS: dict[OrderStatus, set[OrderStatus]] = {
    OrderStatus.created: {OrderStatus.pending, OrderStatus.cancelled},
    OrderStatus.pending: {
        OrderStatus.processing,
        OrderStatus.completed,
        OrderStatus.cancelled,
    },
    OrderStatus.processing: {OrderStatus.completed, OrderStatus.cancelled},
    OrderStatus.completed: set(),
    OrderStatus.cancelled: set(),
}
