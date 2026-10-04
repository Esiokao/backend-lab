import os
from datetime import datetime, timedelta, timezone

import jwt
from dotenv import load_dotenv
from pydantic import ValidationError

from app.schemas.Auth import AccessTokenPayload

# 載入 .env
load_dotenv()


# 從環境變數取得 JWT Secret
JWT_SECRET = os.getenv("JWT_SECRET")

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set")


# JWT 使用的簽章演算法
JWT_ALGORITHM = "HS256"

# Token 有效時間
ACCESS_TOKEN_EXPIRE_MINUTES = 30


def create_access_token(user_id: int) -> str:
    """
    建立 Access Token。

    Token 裡面會放：
    - sub: 使用者 ID
    - exp: Token 到期時間
    """

    # 現在時間
    now = datetime.now(timezone.utc)

    # Token 到期時間
    expires_at = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    # JWT Payload
    payload = {
        "sub": str(user_id),
        "exp": expires_at,
    }

    # 使用 Secret + Algorithm 簽署 JWT
    token = jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )

    return token


def decode_access_token(token: str) -> AccessTokenPayload:
    """
    驗證 JWT 並驗證 Payload。
    """

    try:
        # 驗證 JWT signature、algorithm、expiration。
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )

        # 驗證 JWT Payload 的結構、型別與格式。
        return AccessTokenPayload.model_validate(payload)

    except (jwt.PyJWTError, ValidationError):
        # JWT 或 Payload 驗證失敗。
        raise ValueError("Invalid or expired token")
