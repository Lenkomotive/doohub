"""Add name column to sessions, remove unique constraint from session_key

Revision ID: 004
Revises: 003
Create Date: 2026-03-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("sessions", sa.Column("name", sa.String(200), nullable=False, server_default="untitled"))
    # Drop unique constraint on session_key — key is now a UUID, name is the label
    op.drop_index("ix_sessions_session_key", table_name="sessions")
    op.create_index("ix_sessions_session_key", "sessions", ["session_key"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_sessions_session_key", table_name="sessions")
    op.create_index("ix_sessions_session_key", "sessions", ["session_key"], unique=True)
    op.drop_column("sessions", "name")
