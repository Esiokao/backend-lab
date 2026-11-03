# tests/core/integration/test_global_request_size.py
#
# 全域 body 上限：RequestSizeRoute 由 app.main 的 app.router.route_class
# 統一套用（不再是 users router 專屬）。本檔用非 users 端點驗證——
# size 檢查在 route handler 最外層，先於 auth 依賴與 rate limit，
# 所以未登入也會拿到 413（而非 401）。

MAX_SIZE = 1024 * 1024  # 與 DEFAULT_MAX_REQUEST_SIZE 預設一致（1MB）


def test_oversized_body_rejected_on_cart_endpoint(test_client):
    # cart router 沒有自己的 route_class——能回 413 就代表全域套用成功。
    response = test_client.post(
        "/cart/items",
        content=b"x" * (MAX_SIZE + 1),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413


def test_oversized_body_rejected_on_login(test_client):
    # login 有 per-endpoint @request_size_limit(100KB) 收緊——
    # 1MB 的 body 早就超過 100KB，但同樣 413（兩層上限都拒絕）。
    response = test_client.post(
        "/login",
        content=b"x" * (MAX_SIZE + 1),
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 413


def test_normal_sized_body_passes_size_check(test_client):
    # 未超限的 body 不會被 size 檢查擋下——
    # cart 需要登入，所以拿到的是 401（auth 依賴正常執行 = size 檢查放行）。
    response = test_client.post(
        "/cart/items",
        content=b'{"product_id": 1, "quantity": 1}',
        headers={"Content-Type": "application/json"},
    )

    assert response.status_code == 401
