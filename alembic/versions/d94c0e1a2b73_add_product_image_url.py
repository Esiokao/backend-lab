"""add product image_url

Revision ID: d94c0e1a2b73
Revises: b3f7a2c94d10
Create Date: 2026-10-24 09:40:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d94c0e1a2b73"
down_revision: Union[str, Sequence[str], None] = "b3f7a2c94d10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add image_url to products (nullable, external URL in v1)."""
    op.add_column(
        "products",
        sa.Column("image_url", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    """Remove product image_url."""
    op.drop_column("products", "image_url")
