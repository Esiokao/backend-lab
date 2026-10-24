from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.dependencies import require_admin
from app.database import get_db
from app.models import Category, Product, User
from app.schemas.Product import ProductCreate, ProductResponse

router = APIRouter(prefix="/products")


@router.post(
    "",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
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
