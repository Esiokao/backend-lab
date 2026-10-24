"""add users.last_seen_broadcast_id

Revision ID: a1b2c3d4e5f6
Revises: d9e0f1a2b3c4
Create Date: 2026-10-24 20:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "d9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """廣播已讀水位：記錄使用者最後看過的廣播 id。

    未讀 = id > 水位的廣播（並排除使用者註冊前發布的）。
    """
    op.add_column(
        "users",
        sa.Column("last_seen_broadcast_id", sa.Integer(), nullable=True),
    )
    # 使用者註冊時間：廣播未讀規則（註冊前發布的不算）需要它。
    op.add_column(
        "users",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "created_at")
    op.drop_column("users", "last_seen_broadcast_id")
