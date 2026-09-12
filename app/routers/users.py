from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import UserCreate, UserPatch, UserResponse, UserUpdate


router = APIRouter()


@router.get("/users", response_model=list[UserResponse])
def get_users(
    session: Session = Depends(get_db),
):
    stmt = select(User)
    result = session.execute(stmt)

    return result.scalars().all()


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user(
    user_id: int,
    session: Session = Depends(get_db),
):
    stmt = select(User).where(User.id == user_id)
    result = session.execute(stmt)
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
        update(User)
        .where(User.id == user_id)
        .values(
            name=user.name,
            email=user.email,
        )
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

    stmt = (
        update(User)
        .where(User.id == user_id)
        .values(**update_data)
        .returning(User)
    )

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
    stmt = select(User).where(User.id == user_id)
    result = session.execute(stmt)
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