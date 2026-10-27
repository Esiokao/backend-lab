"""訂單與通知的事件類型：outbox 路由的唯一真相來源。"""

from enum import Enum


class EventType(str, Enum):
    """Outbox 的事件類型（TASK_REGISTRY 的 key、worker 的路由依據）。"""

    order_created = "notifications.order_created"  # 訂單建立
    admin_notification_created = "notifications.admin_created"  # admin 發送的通知
    product_restocked = "notifications.product_restocked"  # 商品補貨
    order_paid = "notifications.order_paid"  # 訂單付款
    order_completed = "notifications.order_completed"  # 訂單完成
    order_cancelled = "notifications.order_cancelled"  # 訂單取消


# ── SSE 推播頻道命名（worker / API 端點共用的約定）──
# 推送內容只是「該刷新了」的提示，資料一律以 DB 為準（輪詢兜底）。


def user_channel(user_id: int) -> str:
    """個人通知頻道：該使用者的 Notification 建立後對此頻道喊話。"""
    return f"notify:user:{user_id}"


BROADCAST_CHANNEL = "notify:broadcast"  # 公告頻道：廣播建立後全體喊一次
