# tests/unit/test_auth.py

from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.core.dependencies import get_current_user
from app.models import User
from app.schemas.Auth import AccessTokenPayload


def test_get_current_user(test_db):
    fake_user = User(
        id=123,
        name="TestUser",
        email="test@example.com",
        password_hash="fake-hash",
        role="user",
    )

    # Fake JWT payload。
    fake_payload = AccessTokenPayload(
        sub=str(fake_user.id),
        exp=9999999999,
    )

    # Fake Authorization credentials。
    fake_credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="fake-token",
    )

    # Fake SQLAlchemy result。
    fake_result = Mock()
    fake_result.scalar_one_or_none.return_value = fake_user

    # Fake Session。
    fake_session = Mock()
    fake_session.execute.return_value = fake_result

    # 暫時把真正的 JWT decoder 換成 Mock。
    with patch(
        "app.core.dependencies.decode_access_token",
        return_value=fake_payload,
    ) as mock_decode:
        # 執行真正的 get_current_user。
        user = get_current_user(
            credentials=fake_credentials,
            session=fake_session,
        )

    # 確認找到正確的 User。
    assert user.id == fake_user.id

    # 確認 decoder 收到正確的 token，而且只呼叫一次。
    mock_decode.assert_called_once_with("fake-token")


def test_get_current_user_invalid_token(test_db):
    # Fake Authorization credentials。
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="fake-token",
    )

    # 假造 JWT 解碼失敗，並確認 API 拋出 401。
    with (
        patch(
            "app.core.dependencies.decode_access_token",
            side_effect=ValueError(),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        get_current_user(
            credentials=credentials,
            session=test_db,
        )

    # 確認無效 JWT 回傳 401。
    assert exc_info.value.status_code == 401


def test_get_current_user_missing_sub(test_db):
    # Fake Authorization credentials。
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="fake-token",
    )

    # decode_access_token() 遇到缺少 sub 的 JWT 時，
    # 應該在 JWT layer 就失敗，而不是回傳 dict。
    with (
        patch(
            "app.core.dependencies.decode_access_token",
            side_effect=ValueError(),
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        get_current_user(
            credentials=credentials,
            session=test_db,
        )

    # 確認無效 JWT 回傳 401。
    assert exc_info.value.status_code == 401


def test_get_current_user_user_not_found(test_db):
    # Fake JWT payload with non-existent user ID。
    fake_payload = AccessTokenPayload(
        sub="9999",
        exp=9999999999,
    )

    # Fake Authorization credentials。
    credentials = HTTPAuthorizationCredentials(
        scheme="Bearer",
        credentials="fake-token",
    )

    # 假造合法 JWT，但對應的 User 不存在。
    with (
        patch(
            "app.core.dependencies.decode_access_token",
            return_value=fake_payload,
        ),
        pytest.raises(HTTPException) as exc_info,
    ):
        get_current_user(
            credentials=credentials,
            session=test_db,
        )

    # 確認找不到 User 時回傳 401。
    assert exc_info.value.status_code == 401

    # 確認錯誤訊息。
    assert exc_info.value.detail == "User not found"
