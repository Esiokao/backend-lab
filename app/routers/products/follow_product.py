from fastapi import HTTPException
from sqlalchemy import func, select

from app.core.dependencies import CurrentUser
from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Product, ProductFollow

router = SizeLimitedAPIRouter(prefix="/products")

# 每位使用者可收藏的商品數上限：保護通知 worker（補貨事件 = follower 數量的
# 通知插入）與 Following 頁的載入成本。
MAX_FOLLOWS_PER_USER = 20


@router.post("/{product_id}/follow")
def follow_product(
    product_id: int,
    current_user: CurrentUser,
    db: DbSession,
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
        # 收藏數量上限：只在「新增」時檢查（取消收藏不受限）。
        follow_count = db.scalar(
            select(func.count())
            .select_from(ProductFollow)
            .where(
                ProductFollow.user_id == current_user.id,
            )
        )
        if follow_count >= MAX_FOLLOWS_PER_USER:
            raise HTTPException(
                status_code=409,
                detail=f"Follow limit reached ({MAX_FOLLOWS_PER_USER} products). Unfollow something first.",
            )

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
    current_user: CurrentUser,
    db: DbSession,
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
