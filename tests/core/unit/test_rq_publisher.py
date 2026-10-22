# tests/core/unit/test_rq_publisher.py

import importlib
from unittest.mock import Mock

import pytest

from app.core.queue import get_task_publisher
from app.core.rq_publisher import TASK_REGISTRY, RQPublisher


def test_enqueue_unknown_task_raises():
    # 未註冊的任務名稱應該在發布當下就被拒絕，
    # 而不是等到 worker 執行時才失敗。
    publisher = RQPublisher(queue=Mock())

    with pytest.raises(ValueError, match="Unknown task"):
        publisher.enqueue("tasks.does_not_exist", {})


def test_enqueue_registered_task():
    # 用注入的 fake queue 驗證任務名稱解析與參數傳遞。
    queue = Mock()
    queue.enqueue.return_value = Mock(id="job-123")

    publisher = RQPublisher(queue=queue)

    job_id = publisher.enqueue(
        "notifications.order_created",
        {"order_id": 42},
    )

    # 任務名稱應該被解析成 worker 可以匯入的函式路徑。
    task_path = TASK_REGISTRY["notifications.order_created"]

    queue.enqueue.assert_called_once_with(
        task_path,
        kwargs={"payload": {"order_id": 42}},
    )

    # 回傳 RQ 的 job id。
    assert job_id == "job-123"


def test_task_registry_paths_are_importable():
    # Registry 裡的每個路徑都必須真的可以匯入。
    # 這裡是最早能抓到「拼字錯誤」的地方；如果等到 worker
    # 執行時才 ModuleNotFoundError，失敗會延遲又脫離現場。
    for task_path in TASK_REGISTRY.values():
        module_name, _, func_name = task_path.rpartition(".")

        module = importlib.import_module(module_name)

        assert callable(getattr(module, func_name)), task_path


def test_get_task_publisher_returns_protocol_compatible_object():
    # 結構化型別：只要提供 enqueue，就符合 TaskPublisher。
    publisher = get_task_publisher()

    assert callable(publisher.enqueue)
