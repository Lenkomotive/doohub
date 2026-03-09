"""Add session mode column, replace interactive boolean

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
        sa.Column("mode", sa.String(30), nullable=True),
    )
    # Backfill from interactive boolean
    op.execute("UPDATE sessions SET mode = 'interactive' WHERE interactive = true")
    op.execute("UPDATE sessions SET mode = 'chat' WHERE interactive = false OR interactive IS NULL")
    op.alter_column("sessions", "mode", nullable=False, server_default="chat")
    op.drop_column("sessions", "interactive")


def downgrade() -> None:
    op.add_column(
        "sessions",
        sa.Column("interactive", sa.Boolean(), nullable=True, server_default=sa.text("false")),
    )
    op.execute("UPDATE sessions SET interactive = true WHERE mode = 'interactive'")
    op.execute("UPDATE sessions SET interactive = false WHERE mode != 'interactive'")
    op.alter_column("sessions", "interactive", nullable=False)
    op.drop_column("sessions", "mode")
