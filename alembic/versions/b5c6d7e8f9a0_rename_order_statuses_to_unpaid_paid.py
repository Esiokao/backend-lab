"""rename order statuses created/pending to unpaid/paid

狀態語意改名（結構不變）：
  created → unpaid   「已建單，未付款」
  pending → paid     「已付款，待出貨」
舊名稱的日常語意與實際業務語意錯位，已造成多次誤解（測試造錯狀態、
取消測錯窗口）。資料遷移只改字串值，狀態機結構與轉移規則不變。

Revision ID: b5c6d7e8f9a0
Revises: a1b2c3d4e5f6
Create Date: 2026-11-01 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b5c6d7e8f9a0"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE orders SET status = 'unpaid' WHERE status = 'created'")
    op.execute("UPDATE orders SET status = 'paid' WHERE status = 'pending'")


def downgrade() -> None:
    op.execute("UPDATE orders SET status = 'created' WHERE status = 'unpaid'")
    op.execute("UPDATE orders SET status = 'pending' WHERE status = 'paid'")
