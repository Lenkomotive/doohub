"""Replace interactive boolean with mode string on sessions

Revision ID: 011
Revises: 010
Create Date: 2026-03-09

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("mode", sa.String(20), nullable=False, server_default="oneshot"),
    )
    # Migrate existing data: interactive=True -> freeform
    op.execute("UPDATE sessions SET mode = 'freeform' WHERE interactive = true")
    op.drop_column("sessions", "interactive")


def downgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("interactive", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.execute("UPDATE sessions SET interactive = true WHERE mode = 'freeform'")
    op.drop_column("sessions", "mode")
