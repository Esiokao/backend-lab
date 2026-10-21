"""add notification outbox

Revision ID: e168878d6177
Revises: 704c8b987b3b
Create Date: 2026-10-19 22:39:52.773927
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# Alembic revision identifiers.
revision: str = "e168878d6177"
down_revision: Union[str, Sequence[str], None] = "704c8b987b3b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """建立 Outbox 資料表與通知事件關聯。"""

    op.create_table(
        "notification_outbox",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="pending",
            nullable=False,
        ),
        sa.Column(
            "attempts",
            sa.Integer(),
            server_default="0",
            nullable=False,
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "idx_notification_outbox_pending",
        "notification_outbox",
        ["status", "available_at"],
        unique=False,
    )

    # 使用明確名稱，避免 Alembic 無法 rollback 未命名 constraint。
    op.add_column(
        "notifications",
        sa.Column("source_event_id", sa.Integer(), nullable=True),
    )

    op.create_unique_constraint(
        "uq_notifications_source_event_id",
        "notifications",
        ["source_event_id"],
    )

    op.create_foreign_key(
        "fk_notifications_source_event_id_notification_outbox",
        "notifications",
        "notification_outbox",
        ["source_event_id"],
        ["id"],
    )


def downgrade() -> None:
    """依照外鍵依賴順序回復資料庫結構。"""

    op.drop_constraint(
        "fk_notifications_source_event_id_notification_outbox",
        "notifications",
        type_="foreignkey",
    )

    op.drop_constraint(
        "uq_notifications_source_event_id",
        "notifications",
        type_="unique",
    )

    op.drop_column("notifications", "source_event_id")

    op.drop_index(
        "idx_notification_outbox_pending",
        table_name="notification_outbox",
    )

    op.drop_table("notification_outbox")
