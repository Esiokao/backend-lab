from decimal import Decimal

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.dependencies import get_current_user
from app.core.request_size import SizeLimitedAPIRouter
from app.database import get_db
from app.models import CartItem, Product, User
from app.routers.orders import create_order
from app.schemas.Cart import CartCheckout, CartItemAdd, CartItemUpdate, CartResponse
from app.schemas.Order import OrderCreate, OrderItemCreate, OrderResponse

router = SizeLimitedAPIRouter(prefix="/cart", tags=["Cart"])


def _get_items(db: Session, user_id: int):
    return db.scalars(
        select(CartItem)
        .options(selectinload(CartItem.product))
        .where(CartItem.user_id == user_id)
        .order_by(CartItem.id)
    ).all()


@router.post("/items", response_model=CartResponse, status_code=status.HTTP_201_CREATED)
def add_to_cart(
    payload: CartItemAdd,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    product = db.scalar(
        select(Product).where(
            Product.id == payload.product_id, Product.is_active.is_(True)
        )
    )
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    item = db.scalar(
        select(CartItem).where(
            CartItem.user_id == current_user.id,
            CartItem.product_id == payload.product_id,
        )
    )
    new_quantity = (
        payload.quantity if item is None else item.quantity + payload.quantity
    )

    # 購物車階段就擋超庫存：讓使用者在點按鈕的當下被擋，而不是結帳時。
    # 結帳的原子檢查（WHERE stock >= quantity）仍是真正防線（並發競態）。
    if new_quantity > 100:
        raise HTTPException(status_code=422, detail="Cart quantity cannot exceed 100")
    if new_quantity > product.stock:
        raise HTTPException(
            status_code=422, detail=f"Only {product.stock} left in stock"
        )

    if item is None:
        item = CartItem(
            user_id=current_user.id,
            product_id=payload.product_id,
            quantity=new_quantity,
        )
        db.add(item)
    else:
        item.quantity = new_quantity

    db.commit()
    return _cart_response(_get_items(db, current_user.id))


@router.get("", response_model=CartResponse)
def get_cart(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    return _cart_response(_get_items(db, current_user.id))


@router.patch("/items/{product_id}", response_model=CartResponse)
def update_cart_item(
    product_id: int,
    payload: CartItemUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.scalar(
        select(CartItem)
        .options(selectinload(CartItem.product))
        .where(CartItem.user_id == current_user.id, CartItem.product_id == product_id)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    if payload.quantity > item.product.stock:
        raise HTTPException(
            status_code=422, detail=f"Only {item.product.stock} left in stock"
        )
    item.quantity = payload.quantity
    db.commit()
    return _cart_response(_get_items(db, current_user.id))


@router.delete("/items/{product_id}", response_model=CartResponse)
def remove_from_cart(
    product_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.scalar(
        select(CartItem).where(
            CartItem.user_id == current_user.id, CartItem.product_id == product_id
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(item)
    db.commit()
    return _cart_response(_get_items(db, current_user.id))


@router.delete("", response_model=CartResponse)
def clear_cart(
    current_user: User = Depends(get_current_user), db: Session = Depends(get_db)
):
    for item in _get_items(db, current_user.id):
        db.delete(item)
    db.commit()
    return {"items": [], "total": Decimal(0)}


@router.post("/checkout", response_model=OrderResponse)
def checkout(
    payload: CartCheckout | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    items = _get_items(db, current_user.id)

    # 前端勾選式結帢：只帶選中的商品建立訂單，其餘留在車上。
    if payload is not None and payload.product_ids is not None:
        wanted = set(payload.product_ids)
        items = [item for item in items if item.product_id in wanted]

    if not items:
        raise HTTPException(status_code=400, detail="Cart is empty")
    order = create_order(
        OrderCreate(
            items=[
                OrderItemCreate(product_id=item.product_id, quantity=item.quantity)
                for item in items
            ]
        ),
        current_user=current_user,
        session=db,
    )
    for item in items:
        db.delete(item)
    db.commit()
    return order


def _cart_response(items: list[CartItem]) -> dict:
    response_items = [
        {
            "product_id": item.product_id,
            "product_name": item.product.name,
            "quantity": item.quantity,
            "unit_price": item.product.price,
            "subtotal": item.product.price * item.quantity,
            "stock": item.product.stock,
        }
        for item in items
    ]
    return {
        "items": response_items,
        "total": sum((item["subtotal"] for item in response_items), Decimal(0)),
    }
