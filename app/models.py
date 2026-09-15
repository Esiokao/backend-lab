from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)

    # One user can have many orders.
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="user",
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Store the ID of the user who owns this order.
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id")
    )

     # Each order belongs to one user.
    user: Mapped["User"] = relationship(
        "User",
        back_populates="orders",
    )