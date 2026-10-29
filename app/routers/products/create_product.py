from fastapi import HTTPException, status

from app.core.dependencies import AdminUser
from app.core.request_size import SizeLimitedAPIRouter
from app.database import DbSession
from app.models import Category, Product
from app.schemas.Product import ProductCreate, ProductResponse

router = SizeLimitedAPIRouter(prefix="/products")


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    payload: ProductCreate,
    db: DbSession,
    _: AdminUser,
):
    if (
        payload.category_id is not None
        and db.get(Category, payload.category_id) is None
    ):
        raise HTTPException(status_code=404, detail="Category not found")

    product = Product(
        name=payload.name,
        description=payload.description,
        image_url=payload.image_url,
        price=payload.price,
        stock=payload.stock,
        category_id=payload.category_id,
    )

    db.add(product)
    db.commit()
    db.refresh(product)

    return product
