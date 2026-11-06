import os
import time

import pytest
import requests

# 通知管線深探針（staging 部署後自動驗證）：
#   admin 發一則定向通知 → 輪詢 unread-count 直到 +1。
# 蓋住完整非同步鏈：api → outbox → dispatcher → RQ → notifications worker → DB。
#
# 前提（deploy-staging workflow 提供）：
#   DEPLOY_PROBE_EMAIL / DEPLOY_PROBE_PASSWORD —— 部署時自動建立並升級 admin 的探針帳號。
#   staging 不設 TURNSTILE_SECRET_KEY（沙盒不上鎖）→ API 登入免 captcha。
#
# 沒有這些 env → 跳過（本機/未設定的環境黃色略過，不紅）。

pytestmark = [
    pytest.mark.deployment,
    pytest.mark.skipif(
        "DEPLOY_PROBE_EMAIL" not in os.environ
        or "DEPLOY_PROBE_PASSWORD" not in os.environ,
        reason="需要 DEPLOY_PROBE_EMAIL/PASSWORD（deploy-staging workflow 注入）",
    ),
]

BASE = os.environ.get("DEPLOY_BASE_URL", "")
PROBE_TITLE_PREFIX = "[deploy-probe]"


def _session() -> requests.Session:
    """登入探針 admin，回傳帶 cookie 的 session。"""
    s = requests.Session()
    s.verify = False
    r = s.post(
        f"{BASE}/api/login",
        json={
            "email": os.environ["DEPLOY_PROBE_EMAIL"],
            "password": os.environ["DEPLOY_PROBE_PASSWORD"],
        },
        timeout=10,
    )
    assert r.status_code in (200, 429), (
        f"probe login failed: {r.status_code} {r.text[:120]}"
    )
    return s


def _unread(s: requests.Session) -> int:
    r = s.get(f"{BASE}/api/notifications/unread-count", timeout=10)
    assert r.status_code == 200, f"unread-count failed: {r.status_code}"
    return int(r.json().get("unread_count", 0))


@pytest.mark.deployment
def test_notification_pipeline_end_to_end():
    s = _session()

    me = s.get(f"{BASE}/api/users/me", timeout=10)
    assert me.status_code == 200, f"probe /users/me failed: {me.status_code}"
    user_id = me.json()["id"]

    before = _unread(s)

    # ① 事件誕生：admin 定向通知 → 202 + outbox event
    title = f"{PROBE_TITLE_PREFIX} {time.strftime('%H:%M:%S')}"
    r = s.post(
        f"{BASE}/api/admin/notifications",
        json={"user_id": user_id, "title": title, "body": "pipeline probe"},
        timeout=10,
    )
    assert r.status_code == 202, f"broadcast rejected: {r.status_code} {r.text[:120]}"

    # ② 輪詢：outbox → dispatcher → RQ → worker → Notification 落庫 → unread +1
    deadline = time.time() + 60
    last = before
    while time.time() < deadline:
        time.sleep(3)
        last = _unread(s)
        if last > before:
            return  # 全鏈通

    pytest.fail(
        f"notification pipeline did not deliver within 60s "
        f"(unread {before} → {last}) — dispatcher/RQ/worker may be down"
    )
