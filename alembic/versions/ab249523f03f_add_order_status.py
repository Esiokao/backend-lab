"""add order status

Revision ID: ab249523f03f
Revises: 69e8cfe3f5f3
Create Date: 2026-10-14 12:29:06.934615

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ab249523f03f"
down_revision: Union[str, Sequence[str], None] = "69e8cfe3f5f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add status to orders and initialize existing orders."""
    op.add_column(
        "orders",
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=False,
            server_default="pending",
        ),
    )

    # Remove the database-level default after existing rows are populated.
    op.alter_column(
        "orders",
        "status",
        server_default=None,
    )


def downgrade() -> None:
    """Remove order status."""
    op.drop_column("orders", "status")
