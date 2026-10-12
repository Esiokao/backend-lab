import logging

logger = logging.getLogger(__name__)


def notify_order_created(payload: dict[str, object]) -> None:
    """處理訂單建立通知；目前只記錄事件，不實際寄信。"""
    order_id = payload.get("order_id")

    if not isinstance(order_id, int):
        raise TypeError("payload must contain an integer order_id")

    logger.info(
        "Order created notification requested: order_id=%s",
        order_id,
    )
