from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import get_db
from app.models import Order, User
from app.schemas import OrderCreate




router = APIRouter()


@router.post("/orders")
def create_order(
    order: OrderCreate,
    session: Session = Depends(get_db),
):
    # Create a new Order object from the request data.
    new_order = Order(
        user_id=order.user_id,
    )

    # Add the order to the current database session.
    session.add(new_order)

    # Save the order to the database.
    session.commit()

    # Refresh the object to get the generated ID.
    session.refresh(new_order)

    return new_order


@router.get("/orders")
def get_orders(
    session: Session = Depends(get_db),
):
    # Build a SELECT statement to get all orders.
    stmt = select(Order)

    # Execute the SQL statement.
    result = session.execute(stmt)

    # Extract Order objects from the result.
    return result.scalars().all()

@router.get("/orders/{order_id}")
def get_order(
    order_id: int,
    session: Session = Depends(get_db),
):
    # Build a SELECT statement for a specific order.
    stmt = select(Order).where(Order.id == order_id)

    # Execute the SQL statement.
    result = session.execute(stmt)

    # Get the Order object if it exists.
    order = result.scalar_one_or_none()

    # Return 404 if the order does not exist.
    if order is None:
        raise HTTPException(
            status_code=404,
            detail="Order not found",
        )

    return order

@router.get("/users/{user_id}/orders")
def get_user_orders(
    user_id: int,
    session: Session = Depends(get_db),
):
    # Build a SELECT statement for orders belonging to this user.
    stmt = select(Order).where(Order.user_id == user_id)

    # Execute the SQL statement.
    result = session.execute(stmt)

    # Extract Order objects from the result.
    return result.scalars().all()

@router.get("/users-with-orders")
def get_users_with_orders(
    session: Session = Depends(get_db),
):
    users = session.execute(
    select(User).options(
        selectinload(User.orders)
    )
).scalars().all()

    for user in users:
        print(user.name, len(user.orders))

    return {
    "users": [
        {
            "name": user.name,
            "order_count": len(user.orders),
        }
        for user in users
    ]
}