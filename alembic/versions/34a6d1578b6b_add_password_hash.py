"""add password hash

Revision ID: 34a6d1578b6b
Revises: 1836c17f9a01
Create Date: 2026-09-16 02:27:50.493766
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "34a6d1578b6b"
down_revision: Union[str, Sequence[str], None] = "1836c17f9a01"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    op.add_column(
        "users",
        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=True,
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_column(
        "users",
        "password_hash",
    )
