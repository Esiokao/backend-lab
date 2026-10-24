"""add catalogs and product catalog references

Revision ID: b7c4d5e6f708
Revises: a77edb72fa28
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c4d5e6f708"
down_revision: Union[str, Sequence[str], None] = "a77edb72fa28"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "catalogs",
        sa.Column("id", sa.Integer(), sa.Identity(), primary_key=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.add_column(
        "products",
        sa.Column("catalog_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_products_catalog_id_catalogs",
        "products",
        "catalogs",
        ["catalog_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_products_catalog_id_catalogs",
        "products",
        type_="foreignkey",
    )
    op.drop_column("products", "catalog_id")
    op.drop_table("catalogs")
