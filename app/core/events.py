"""集中管理系統使用的事件類型。"""

# 訂單事件
ORDER_CREATED = "notifications.order_created"

# 任務名稱對應到 Worker 可以匯入的函式路徑。
TASK_REGISTRY: dict[str, str] = {
    "notifications.order_created": ("app.workers.notifications.notify_order_created"),
}
