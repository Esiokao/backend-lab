from fastapi import HTTPException
from sqlalchemy import select

from app.core.dependencies import AdminUser
from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Category
from app.schemas.Category import CategoryReorderRequest

router = SizeLimitedAPIRouter(prefix="/categories")


@router.put("/reorder", response_model=list[int])
def reorder_categories(
    payload: CategoryReorderRequest,
    db: DbSession,
    _: AdminUser,
):
    """批次重排分類：body 給完整 id 清單（按新順序），單一交易寫入 sort_order=index。

    只接受「全量」清單——部分重排的語意（拖曳跨頁）第一版不支援。
    """
    ids = payload.category_ids

    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=400, detail="Duplicate category ids")

    existing = db.scalars(select(Category.id)).all()
    if set(ids) != set(existing):
        raise HTTPException(
            status_code=400,
            detail="category_ids must contain exactly all category ids",
        )

    # 單一交易：按清單位置寫 sort_order。
    for index, category_id in enumerate(ids):
        category = db.get(Category, category_id)
        category.sort_order = index

    db.commit()
    return ids
