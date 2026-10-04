import pytest
from pydantic import ValidationError

from app.schemas.Auth import AccessTokenPayload


def test_access_token_payload_valid():
    # 建立合法的 JWT Payload。
    payload = AccessTokenPayload(
        sub="123",
        exp=1234567890,
    )

    # 合法 Payload 應該成功建立。
    assert payload.sub == "123"
    assert payload.exp == 1234567890


def test_access_token_payload_missing_sub():
    # 缺少 sub。
    with pytest.raises(ValidationError):
        AccessTokenPayload(
            exp=1234567890,
        )


def test_access_token_payload_null_sub():
    # sub 不允許為 None。
    with pytest.raises(ValidationError):
        AccessTokenPayload(
            sub=None,
            exp=1234567890,
        )


def test_access_token_payload_non_string_sub():
    # sub 必須是字串。
    with pytest.raises(ValidationError):
        AccessTokenPayload(
            sub=[],
            exp=1234567890,
        )


def test_access_token_payload_empty_sub():
    # 空字串不符合 User ID 的格式。
    with pytest.raises(ValidationError):
        AccessTokenPayload(
            sub="",
            exp=1234567890,
        )


def test_access_token_payload_non_numeric_sub():
    # sub 不能包含非數字字元。
    with pytest.raises(ValidationError):
        AccessTokenPayload(
            sub="abc",
            exp=1234567890,
        )


def test_access_token_payload_alphanumeric_sub():
    # sub 不能是混合字串。
    with pytest.raises(ValidationError):
        AccessTokenPayload(
            sub="123abc",
            exp=1234567890,
        )


def test_access_token_payload_missing_exp():
    # 缺少 exp。
    with pytest.raises(ValidationError):
        AccessTokenPayload(
            sub="123",
        )


def test_access_token_payload_invalid_exp():
    # exp 必須是有效的整數。
    with pytest.raises(ValidationError):
        AccessTokenPayload(
            sub="123",
            exp="not-a-timestamp",
        )
