"""create initial users and orders tables

Revision ID: 1836c17f9a01
Revises:
Create Date: 2026-09-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "1836c17f9a01"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.UniqueConstraint("email", name="users_email_unique"),
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    op.create_index("idx_orders_user_id", "orders", ["user_id"])


def downgrade() -> None:
    op.drop_index("idx_orders_user_id", table_name="orders")
    op.drop_table("orders")
    op.drop_table("users")
