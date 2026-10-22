"""allow notification fan out

Revision ID: e388dc138f83
Revises: 6bfb711873b9
Create Date: 2026-10-22 15:32:42.664372

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "e388dc138f83"
down_revision: Union[str, Sequence[str], None] = "6bfb711873b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint(
        "uq_notifications_source_event_id",
        "notifications",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_notifications_source_event_user",
        "notifications",
        ["source_event_id", "user_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_notifications_source_event_user",
        "notifications",
        type_="unique",
    )

    op.create_unique_constraint(
        "uq_notifications_source_event_id",
        "notifications",
        ["source_event_id"],
    )
