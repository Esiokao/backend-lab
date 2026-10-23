"""訂單與通知的事件類型：outbox 路由的唯一真相來源。"""

from enum import Enum


class EventType(str, Enum):
    """Outbox 的事件類型（TASK_REGISTRY 的 key、worker 的路由依據）。"""

    order_created = "notifications.order_created"  # 訂單建立
    admin_notification_created = "notifications.admin_created"  # admin 發送的通知
    product_restocked = "notifications.product_restocked"  # 商品補貨
    order_paid = "notifications.order_paid"  # 訂單付款
