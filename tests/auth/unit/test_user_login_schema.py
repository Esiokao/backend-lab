import pytest
from pydantic import ValidationError

from app.schemas.Auth import UserLogin


def test_user_login_valid():
    mock_login_data = UserLogin(email="test@example.com", password="password")

    assert mock_login_data.email == "test@example.com"
    assert mock_login_data.password == "password"


def test_user_login_invalid_email():
    # expect ValidationError for invalid email
    with pytest.raises(ValidationError):
        UserLogin(
            email="not-an-email",
            password="testpassword",
        )


def test_user_login_password_too_short():
    # 密碼少於 8 個字元時，應該無法建立 UserLogin。
    with pytest.raises(ValidationError):
        UserLogin(
            email="test@example.com",
            password="1234567",
        )


def test_user_login_password_min_length():
    # 8 個字元剛好符合最小長度。
    user_login = UserLogin(
        email="test@example.com",
        password="12345678",
    )

    # 剛好在 boundary 上應該是合法的。
    assert user_login.password == "12345678"


def test_user_login_password_max_length():
    # 128 個字元剛好符合最大長度。
    user_login = UserLogin(
        email="test@example.com",
        password="a" * 128,
    )

    assert user_login.password == "a" * 128


def test_user_login_password_too_long():
    # 密碼超過 128 個字元時，應該無法建立 UserLogin。
    with pytest.raises(ValidationError):
        UserLogin(
            email="test@example.com",
            password="a" * 129,
        )


def test_user_login_missing_email():
    # 缺少 email 時，應該無法建立 UserLogin。
    with pytest.raises(ValidationError):
        UserLogin(
            password="testpassword",
        )


def test_user_login_missing_password():
    # 缺少 password 時，應該無法建立 UserLogin。
    with pytest.raises(ValidationError):
        UserLogin(
            email="test@example.com",
        )


def test_user_login_email_none():
    # email 不允許為 None。
    with pytest.raises(ValidationError):
        UserLogin(
            email=None,
            password="testpassword",
        )


def test_user_login_password_none():
    # password 不允許為 None。
    with pytest.raises(ValidationError):
        UserLogin(
            email="test@example.com",
            password=None,
        )
