from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.jwt import decode_access_token
from app.database import get_db
from app.models import User


# 告訴 FastAPI：
# 我需要從 Authorization: Bearer <token> 拿 JWT
bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    session: Session = Depends(get_db),
) -> User:
    """
    從 JWT 找出目前登入的 User。
    """

    token = credentials.credentials

    # 驗證並解析 JWT
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
        )

    # 從 JWT payload 取得 user ID
    user_id = payload.get("sub")

    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid token",
        )

    # 根據 user ID 查詢 User
    stmt = select(User).where(User.id == int(user_id))
    result = session.execute(stmt)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="User not found",
        )

    return user


def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    # 只有 admin 可以通過
    if current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    return current_user
