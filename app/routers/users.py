from fastapi import Cookie, HTTPException, Request, Response
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import AdminUser, CurrentUser
from app.core.jwt import create_access_token
from app.core.rate_limit import rate_limit
from app.core.request_size import SizeLimitedAPIRouter, request_size_limit
from app.core.security import hash_password, verify_password
from app.core.session import (
    COOKIE_NAME,
    REMEMBER_TTL_SECONDS,
    SESSION_TTL_SECONDS,
    cookie_secure,
    create_session,
    delete_session,
    revoke_all_user_sessions,
)
from app.core.turnstile import verify_turnstile_token
from app.database import DbSession
from app.models import User
from app.schemas.Auth import DemoLogin, UserLogin
from app.schemas.User import UserCreate, UserPatch, UserResponse, UserUpdate

# body 上限由 app.main 的全域 route_class（RequestSizeRoute）統一套用。
router = SizeLimitedAPIRouter(tags=["Users"])


def _ensure_self_or_admin(current_user: User, user_id: int) -> None:
    # 僅本人或 admin 可以存取/修改該使用者的資料。
    if current_user.id != user_id and current_user.role != "admin":
        raise HTTPException(
            status_code=403,
            detail="You can only manage your own account",
        )


@router.get("/users", response_model=list[UserResponse])
def get_users(
    session: DbSession,
    _: AdminUser,
):
    # 只有 admin 可以列出全部使用者；固定依 id 排序（不然 Postgres 回堆積順序）。
    result = session.execute(select(User).order_by(User.id))
    return result.scalars().all()


@router.get("/users/me", response_model=UserResponse)
def get_current_user_info(
    current_user: CurrentUser,
):
    # get_current_user 已經完成 JWT 驗證並找到 User
    return current_user


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    session: DbSession,
    current_user: CurrentUser,
):
    # 僅本人或 admin 可以查看使用者詳情。
    _ensure_self_or_admin(current_user, user_id)

    result = session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return user


@router.post("/users", response_model=UserResponse)
def create_user(
    user: UserCreate,
    session: DbSession,
):
    new_user = User(
        name=user.name,
        email=user.email,
        password_hash=hash_password(user.password),
    )

    session.add(new_user)

    try:
        session.commit()
        session.refresh(new_user)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email already exists",
        )

    return new_user


@router.put("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    user: UserUpdate,
    session: DbSession,
    current_user: CurrentUser,
):
    # 僅本人或 admin 可以更新。
    _ensure_self_or_admin(current_user, user_id)

    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(name=user.name, email=user.email)
        .returning(User)
    )

    try:
        result = session.execute(stmt)
        updated_user = result.scalar_one_or_none()
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email already exists",
        )

    if updated_user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return updated_user


@router.patch("/users/{user_id}", response_model=UserResponse)
def patch_user(
    user_id: int,
    user: UserPatch,
    session: DbSession,
    current_user: CurrentUser,
):
    # 僅本人或 admin 可以修改（含改密碼）。
    _ensure_self_or_admin(current_user, user_id)

    update_data = user.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields to update",
        )

    # 改密碼時要撤銷該使用者的全部 session。
    password_changed = "password" in update_data

    if password_changed:
        # 明文密碼轉成雜湊後寫入 password_hash 欄位。
        raw_password = update_data.pop("password")
        update_data["password_hash"] = hash_password(raw_password)

    stmt = update(User).where(User.id == user_id).values(**update_data).returning(User)

    try:
        result = session.execute(stmt)
        updated_user = result.scalar_one_or_none()

        if updated_user is None:
            session.rollback()
            raise HTTPException(
                status_code=404,
                detail="User not found",
            )

        session.commit()

        # 密碼已成功更換，舊 session 全部失效（被盜用的 session 也一併撤銷）。
        if password_changed:
            revoke_all_user_sessions(user_id)
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email already exists",
        )

    return updated_user


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    session: DbSession,
    _: AdminUser,
):
    # 只有 admin 可以刪除使用者。
    result = session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    try:
        session.delete(user)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="User cannot be deleted because it has related orders",
        )

    return {"message": "User deleted"}


@request_size_limit(100 * 1024)
@router.post(
    "/login",
    responses={
        429: {"description": "Too Many Requests"},
    },
)
# 用 DEFAULT_RATE_LIMIT（prod 5/min；e2e job 的 env 設 50）——
# 寫死 5 會讓 e2e 的連續登入擠進配額樂透（fixture 沒檢查 429 → 下游 401 連環）。
@rate_limit(window=60)
async def login(
    request: Request,
    response: Response,
    user: UserLogin,
    session: DbSession,
):
    # Turnstile（env-gated）：TURNSTILE_SECRET_KEY 有設的環境（正式站）
    # 才驗 token；dev / pytest / e2e 沒設 → 無感跳過。
    import os

    if os.getenv("TURNSTILE_SECRET_KEY"):
        token = (user.turnstile_token or "").strip()
        if not token:
            raise HTTPException(status_code=401, detail="Captcha token missing")
        await verify_turnstile_token(
            token, request.client.host if request.client else None
        )

    # 查詢登入使用者。
    result = session.execute(select(User).where(User.email == user.email))

    db_user = result.scalar_one_or_none()

    # Email 不存在或密碼錯誤。
    if (
        db_user is None
        or db_user.password_hash is None
        or not verify_password(user.password, db_user.password_hash)
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    # 建立 Access Token（過渡期保留給非瀏覽器客戶端）。
    access_token = create_access_token(db_user.id)

    # 建立 session 並設定 HttpOnly cookie：
    # JS 讀不到（防 XSS 偷取）、只走 https（Secure）、
    # SameSite=strict 擋 CSRF。
    # 每次登入都產生全新 sid，天然防 session fixation。
    # 「Keep me signed in」：session 與 cookie 都用 7 天 TTL
    # （滑動過期照常適用——一週內有活動就一直續；預設只有 30 分鐘）。
    session_ttl = REMEMBER_TTL_SECONDS if user.remember_me else SESSION_TTL_SECONDS
    sid = create_session(db_user.id, ttl_seconds=session_ttl)

    response.set_cookie(
        key=COOKIE_NAME,
        value=sid,
        max_age=session_ttl,
        path="/",
        httponly=True,
        secure=cookie_secure(),
        samesite="strict",
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }


@router.post("/auth/demo-login")
@rate_limit(window=60)
async def demo_login(
    request: Request,
    response: Response,
    payload: DemoLogin | None = None,
    *,
    db: DbSession,
):
    """demo 探索登入：免帳密發一個唯讀 admin session（面試官/訪客用）。

    帳號 demo@demo.esiokao.shop 自動建立（role=admin、password_hash=None →
    密碼登入永遠 401，這個帳號只能透過本端點進場）。
    防線與 /login 同等：Turnstile（env-gated）+ rate limit；
    唯讀性由 session 的 read_only 標記在 require_admin 強制執行。
    """
    import os

    if os.getenv("TURNSTILE_SECRET_KEY"):
        token = (payload.turnstile_token if payload else None) or ""
        if not token:
            raise HTTPException(status_code=401, detail="Captcha token missing")
        await verify_turnstile_token(
            token, request.client.host if request.client else None
        )

    demo_email = "demo@demo.esiokao.shop"
    user = db.execute(select(User).where(User.email == demo_email)).scalar_one_or_none()

    if user is None:
        user = User(
            name="Demo Viewer",
            email=demo_email,
            role="admin",
            password_hash=None,
        )
        db.add(user)
        db.flush()
    elif user.role != "admin":
        # 防呆：被手動改掉 role 的話，demo-login 時自動修回。
        user.role = "admin"

    db.commit()
    db.refresh(user)

    # 唯讀 session：不發 access_token（Bearer 路徑無法繞過唯讀限制）。
    sid = create_session(user.id, read_only=True)

    response.set_cookie(
        key=COOKIE_NAME,
        value=sid,
        max_age=SESSION_TTL_SECONDS,
        path="/",
        httponly=True,
        secure=cookie_secure(),
        samesite="strict",
    )

    return {"ok": True}


@router.post("/logout")
def logout(
    response: Response,
    session_cookie: str | None = Cookie(None, alias=COOKIE_NAME),
):
    # 刪除 Redis session → 該 sid 立即失效（真登出，JWT 做不到的事）。
    if session_cookie:
        delete_session(session_cookie)

    # 清除瀏覽器端的 cookie。
    response.delete_cookie(
        key=COOKIE_NAME,
        path="/",
        httponly=True,
        secure=cookie_secure(),
        samesite="strict",
    )

    return {"status": "ok"}
