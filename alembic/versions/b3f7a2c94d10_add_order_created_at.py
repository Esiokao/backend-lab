"""add order created_at

Revision ID: b3f7a2c94d10
Revises: 8869d8514a58
Create Date: 2026-10-23 10:30:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b3f7a2c94d10"
down_revision: Union[str, Sequence[str], None] = "8869d8514a58"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add created_at to orders; existing rows backfill with now()."""
    op.add_column(
        "orders",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )


def downgrade() -> None:
    """Remove order created_at."""
    op.drop_column("orders", "created_at")
