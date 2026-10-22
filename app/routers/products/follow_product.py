from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.dependencies import get_current_user
from app.database import get_db
from app.models import Product, ProductFollow, User

router = APIRouter()


@router.post("/{product_id}/follow")
def follow_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 先確認商品存在，避免建立指向不存在商品的關注資料。
    product = db.get(Product, product_id)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    # 查詢目前使用者是否已經關注這個商品。
    # ProductFollow 的複合主鍵也會在資料庫層防止重複。
    existing = db.scalar(
        select(ProductFollow).where(
            ProductFollow.user_id == current_user.id,
            ProductFollow.product_id == product_id,
        )
    )

    # 只有尚未關注時才新增資料。
    # 重複呼叫 endpoint 會保持成功，不會產生 duplicate error。
    if existing is None:
        db.add(
            ProductFollow(
                user_id=current_user.id,
                product_id=product_id,
            )
        )
        db.commit()

    return {"following": True}


@router.delete("/{product_id}/follow")
def unfollow_product(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 只尋找目前登入使用者自己的關注資料。
    follow = db.scalar(
        select(ProductFollow).where(
            ProductFollow.user_id == current_user.id,
            ProductFollow.product_id == product_id,
        )
    )

    # 沒有關注時維持成功，讓 DELETE 具備冪等性。
    if follow is not None:
        db.delete(follow)
        db.commit()

    return {"following": False}
