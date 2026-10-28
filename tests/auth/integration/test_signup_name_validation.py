# tests/auth/integration/test_signup_name_validation.py
#
# 後端守門：name 欄位 trim + 拒絕純空白（前端 zod 已做同樣的事，
# 這裡驗證直連 API 的 client 也逃不過——前端驗證是體驗，後端才是契約）。


def test_signup_rejects_whitespace_only_name(test_client):
    response = test_client.post(
        "/users",
        json={
            "name": "   ",
            "email": "blank-name@example.com",
            "password": "sup3rsecret",
        },
    )

    assert response.status_code == 422


def test_signup_trims_surrounding_whitespace(test_client):
    response = test_client.post(
        "/users",
        json={
            "name": "  Pi Tester  ",
            "email": "trim-name@example.com",
            "password": "sup3rsecret",
        },
    )

    assert response.status_code in (200, 201)
    assert response.json()["name"] == "Pi Tester"


def test_signup_keeps_internal_spaces(test_client):
    response = test_client.post(
        "/users",
        json={
            "name": "Pi Tester",
            "email": "full-name@example.com",
            "password": "sup3rsecret",
        },
    )

    assert response.status_code in (200, 201)
    assert response.json()["name"] == "Pi Tester"
