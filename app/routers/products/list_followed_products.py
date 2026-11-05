from fastapi import Response
from sqlalchemy import select

from app.core.dependencies import CurrentUser
from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Product, ProductFollow
from app.schemas.Product import ProductResponse

router = SizeLimitedAPIRouter(prefix="/products")


@router.get("/followed")
def list_followed_products(
    current_user: CurrentUser,
    db: DbSession,
    response: Response,
):
    """目前使用者關注的商品——ids（storefront 點亮星星）+ 完整商品（Following 頁）。

    items 按收藏時間新 → 舊排序。
    ⚠️ 必須註冊在 GET /products/{product_id} 之前，否則 "followed"
    會被吃成 product_id 路徑參數。
    """
    rows = db.execute(
        select(ProductFollow.product_id, Product)
        .join(Product, Product.id == ProductFollow.product_id)
        .where(ProductFollow.user_id == current_user.id)
        .order_by(
            ProductFollow.created_at.desc(),
            ProductFollow.product_id.desc(),  # 同毫秒的 tie-breaker
        )
    ).all()

    items = [ProductResponse.model_validate(product) for _, product in rows]

    response.headers["Cache-Control"] = "no-store"
    return {
        "product_ids": [product.id for _, product in rows],
        "count": len(items),
        "items": items,
    }
