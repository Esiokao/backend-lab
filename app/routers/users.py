from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.core.jwt import create_access_token
from app.core.rate_limit import rate_limit
from app.core.request_size import RequestSizeRoute, request_size_limit
from app.core.security import hash_password, verify_password
from app.database import get_db
from app.models import User
from app.schemas.Auth import UserLogin
from app.schemas.User import UserCreate, UserPatch, UserResponse, UserUpdate

router = APIRouter(
    route_class=RequestSizeRoute,
)


@router.get("/users", response_model=list[UserResponse])
def get_users(
    session: Session = Depends(get_db),
):
    result = session.execute(select(User))
    return result.scalars().all()


@router.get("/users/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user),
):
    # get_current_user 已經完成 JWT 驗證並找到 User
    return current_user


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    session: Session = Depends(get_db),
):
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
    session: Session = Depends(get_db),
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
    session: Session = Depends(get_db),
):
    stmt = (
        update(User).where(User.id == user_id).values(name=user.name, email=user.email)
    )

    try:
        result = session.execute(stmt)
        session.commit()
    except IntegrityError:
        session.rollback()
        raise HTTPException(
            status_code=409,
            detail="Email already exists",
        )

    if result.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="User not found",
        )

    return {
        "id": user_id,
        "name": user.name,
        "email": user.email,
    }


@router.patch("/users/{user_id}", response_model=UserResponse)
def patch_user(
    user_id: int,
    user: UserPatch,
    session: Session = Depends(get_db),
):
    update_data = user.model_dump(exclude_unset=True)

    if not update_data:
        raise HTTPException(
            status_code=400,
            detail="No fields to update",
        )

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
    session: Session = Depends(get_db),
):
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
@rate_limit(limit=5, window=60)
def login(
    request: Request,
    user: UserLogin,
    session: Session = Depends(get_db),
):
    # 查詢登入使用者。
    result = session.execute(select(User).where(User.email == user.email))

    db_user = result.scalar_one_or_none()

    # Email 不存在或密碼錯誤。
    if db_user is None or not verify_password(
        user.password,
        db_user.password_hash,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password",
        )

    # 建立 Access Token。
    access_token = create_access_token(db_user.id)

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }
