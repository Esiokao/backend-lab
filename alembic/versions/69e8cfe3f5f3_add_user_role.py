"""add user role

Revision ID: 69e8cfe3f5f3
Revises: 34a6d1578b6b
Create Date: 2026-09-20 13:00:50.614123
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "69e8cfe3f5f3"
down_revision: Union[str, Sequence[str], None] = "34a6d1578b6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # 新增 User role，既有使用者預設為 user
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=20),
            nullable=False,
            server_default="user",
        ),
    )


def downgrade() -> None:
    """Downgrade schema."""

    # 移除 User role
    op.drop_column("users", "role")
