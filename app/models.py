from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)

from app.core.enums import OrderStatus


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # User's role for RBAC.
    role: Mapped[str] = mapped_column(
        String(20),
        default="user",
        nullable=False,
    )

    # One user can have many orders.
    orders: Mapped[list["Order"]] = relationship(
        "Order",
        back_populates="user",
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)

    # Store the ID of the user who owns this order.
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))

    # 訂單建立時間：排序、顯示與分析都用得到。
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Index the user_id column for faster lookups.
    __table_args__ = (Index("idx_orders_user_id", "user_id"),)

    # Each order belongs to one user.
    user: Mapped["User"] = relationship(
        "User",
        back_populates="orders",
    )
    # Track the current state of the order.
    status: Mapped[str] = mapped_column(
        String(20),
        default=OrderStatus.created.value,
        nullable=False,
    )

    # 訂單明細：一張訂單 N 個商品（unit_price 為下單當下的價格快照）。
    items: Mapped[list["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )


class OrderItem(Base):
    """訂單明細：一張訂單內的單一商品列。

    unit_price 是下單當下的價格快照 ——
    商品之後改價不影響歷史訂單（歷史正確性）。
    """

    __tablename__ = "order_items"

    id: Mapped[int] = mapped_column(primary_key=True)

    order_id: Mapped[int] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"),
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id"),
    )

    quantity: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    unit_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("order_id", "product_id", name="uq_order_items_order_product"),
        Index("idx_order_items_order", "order_id"),
        Index("idx_order_items_product", "product_id"),
    )

    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items",
    )

    product: Mapped["Product"] = relationship(
        "Product",
    )


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"),
        nullable=False,
    )

    type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
    )

    data: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    read_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    source_event_id: Mapped[int | None] = mapped_column(
        ForeignKey("notification_outbox.id"),
        nullable=True,
    )

    __table_args__ = (
        Index("idx_notifications_user_created", "user_id", "created_at"),
        UniqueConstraint(
            "source_event_id",
            "user_id",
            name="uq_notifications_source_event_user",
        ),
    )


class NotificationOutbox(Base):
    """保存待發布的通知事件，讓背景工作失敗後可以恢復。"""

    __tablename__ = "notification_outbox"

    id: Mapped[int] = mapped_column(primary_key=True)

    # 事件類型，例如 order_created。
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)

    # 保存建立通知需要的資料，避免依賴記憶體中的任務。
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)

    # pending：等待發布；dispatched：已發布；processed：已完成。
    status: Mapped[str] = mapped_column(
        String(20),
        default="pending",
        server_default="pending",
        nullable=False,
    )

    # 累計發布或重試次數。
    attempts: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    # 允許重試的時間，Dispatcher 可用它篩選待處理事件。
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    dispatched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    processed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # 保留最後一次錯誤，方便排查發布失敗的原因。
    last_error: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        Index(
            "idx_notification_outbox_pending",
            "status",
            "available_at",
        ),
    )


class NotificationBroadcast(Base):
    __tablename__ = "notification_broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True)

    type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )

    body: Mapped[str] = mapped_column(
        String(2000),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # v1：只存外部圖片的 URL（不上傳）。上傳功能另開（本地磁碟或 MinIO）。
    image_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    # 商品可以不屬於任何分類
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id"),
        nullable=True,
    )

    stock: Mapped[int] = mapped_column(
        Integer,
        default=0,
        server_default="0",
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default="true",
        nullable=False,
    )

    category: Mapped["Category | None"] = relationship(
        "Category",
        back_populates="products",
    )


class ProductFollow(Base):
    __tablename__ = "product_follows"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # 取得這個分類底下的所有商品
    products: Mapped[list["Product"]] = relationship(
        "Product",
        back_populates="category",
    )
