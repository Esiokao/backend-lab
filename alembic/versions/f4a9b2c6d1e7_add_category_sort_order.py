"""add category sort_order"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f4a9b2c6d1e7"
down_revision: Union[str, Sequence[str], None] = "c1d2e3f4a5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "categories",
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
    )
    # 既有列按 id 順序回填（與舊的 id 排序行為一致，使用者無感）。
    op.execute("UPDATE categories SET sort_order = id")


def downgrade() -> None:
    op.drop_column("categories", "sort_order")
