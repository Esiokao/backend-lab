from fastapi import Cookie, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.jwt import decode_access_token
from app.core.session import COOKIE_NAME, get_session_user_id
from app.database import get_db
from app.models import User

# 告訴 FastAPI：
# 我需要從 Authorization: Bearer <token> 拿 JWT。
# auto_error=False：沒帶 header 時回 None，由我們自己決定 401 ——
# 這樣「沒有 Bearer 但有 cookie」的瀏覽器請求才能通過。
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session_cookie: str | None = Cookie(None, alias=COOKIE_NAME),
    session: Session = Depends(get_db),
) -> User:
    """從 cookie session 或 Bearer JWT 找出目前登入的 User。

    瀏覽器走 cookie session（優先）；
    非瀏覽器客戶端（過渡期）走 Bearer JWT。
    兩條路最後都匯流到同一段 DB 查詢。
    """
    user_id: int | None = None

    # 1. Cookie session：Redis 查 sid → user_id（含滑動續期）。
    if session_cookie:
        user_id = get_session_user_id(session_cookie)

    # 2. Bearer JWT：過渡期相容路徑。
    elif credentials is not None:
        token = credentials.credentials

        # 驗證 JWT 與 Payload。
        try:
            token_data = decode_access_token(token)
        except ValueError:
            raise HTTPException(
                status_code=401,
                detail="Invalid or expired token",
            )

        # Payload validation 已經保證 sub 是數字字串。
        user_id = int(token_data.sub)

    # 兩種憑證都沒有。
    if user_id is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
        )

    # 根據 User ID 查詢 User。
    stmt = select(User).where(User.id == user_id)
    result = session.execute(stmt)
    user = result.scalar_one_or_none()

    # Token 對應的 User 不存在。
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
