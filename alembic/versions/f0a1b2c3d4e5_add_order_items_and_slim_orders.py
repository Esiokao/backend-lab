"""add order_items and slim orders

Revision ID: f0a1b2c3d4e5
Revises: d94c0e1a2b73
Create Date: 2026-10-24 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f0a1b2c3d4e5"
down_revision: Union[str, Sequence[str], None] = "d94c0e1a2b73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add order_items, migrate legacy order product data, slim orders."""
    # ① 建 order_items（明細表）。
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), autoincrement=True, primary_key=True),
        sa.Column(
            "order_id",
            sa.Integer(),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id"),
            nullable=False,
        ),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "order_id", "product_id", name="uq_order_items_order_product"
        ),
    )
    op.create_index("idx_order_items_order", "order_items", ["order_id"])
    op.create_index("idx_order_items_product", "order_items", ["product_id"])

    # ② 資料搬移：既有訂單的 product_id/quantity → order_items。
    #    unit_price 用商品現價回填（歷史價格在 products 改價前的近似值）。
    #    product_id 為 NULL 的最早期訂單（商品功能上線前）沒有明細可搬，略過。
    op.execute(
        """
        INSERT INTO order_items (order_id, product_id, quantity, unit_price)
        SELECT o.id, o.product_id, o.quantity, p.price
        FROM orders o
        JOIN products p ON p.id = o.product_id
        WHERE o.product_id IS NOT NULL
        """
    )

    # ③ orders 瘦身：product_id/quantity 已搬進 order_items，移除欄位。
    op.drop_column("orders", "product_id")
    op.drop_column("orders", "quantity")

    # ④ 新訂單的初始狀態改為 created（model default 同步）。
    op.alter_column(
        "orders",
        "status",
        existing_type=sa.String(20),
        server_default="created",
    )


def downgrade() -> None:
    """還原單商品結構。

    注意：多明細訂單無法完整還原 —— 每張訂單取第一筆明細回填，
    其餘明細的資料會遺失（downgrade 本來就是破壞性操作）。
    """
    # ① 加回 orders.product_id / quantity（從 order_items 的第一筆回填）。
    op.add_column(
        "orders",
        sa.Column(
            "product_id",
            sa.Integer(),
            sa.ForeignKey("products.id"),
            nullable=True,
        ),
    )
    op.add_column(
        "orders",
        sa.Column("quantity", sa.Integer(), nullable=True),
    )

    op.execute(
        """
        UPDATE orders o SET
            product_id = agg.product_id,
            quantity = agg.quantity
        FROM (
            SELECT order_id, MIN(id) AS first_item_id
            FROM order_items
            GROUP BY order_id
        ) first_items
        JOIN order_items oi ON oi.id = first_items.first_item_id
        WHERE o.id = first_items.order_id
        """
    )

    # ② 刪 order_items。
    op.drop_table("order_items")

    # ③ 收緊 NOT NULL（沒有明細的訂單會擋住 —— 如有此情況先手動處理）。
    op.alter_column(
        "orders",
        "product_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "orders",
        "quantity",
        existing_type=sa.Integer(),
        nullable=False,
    )

    # ④ 狀態預設回退。
    op.alter_column(
        "orders",
        "status",
        existing_type=sa.String(20),
        server_default="pending",
    )
