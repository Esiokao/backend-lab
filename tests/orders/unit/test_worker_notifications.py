# tests/orders/unit/test_worker_notifications.py

import logging

import pytest

from app.workers.notifications import notify_order_created


def test_notify_order_created_logs_order_id(caplog):
    # 正常 payload 應該記錄訂單 ID，不拋出例外。
    with caplog.at_level(logging.INFO, logger="app.workers.notifications"):
        notify_order_created({"order_id": 42})

    assert "order_id=42" in caplog.text


def test_notify_order_created_rejects_missing_order_id():
    # 缺少 order_id 應該讓任務失敗，
    # 失敗的 job 會進 FailedJobRegistry 等待處理。
    with pytest.raises(TypeError, match="order_id"):
        notify_order_created({})


def test_notify_order_created_rejects_non_integer_order_id():
    # order_id 必須是整數；字串也不接受。
    with pytest.raises(TypeError, match="order_id"):
        notify_order_created({"order_id": "42"})
