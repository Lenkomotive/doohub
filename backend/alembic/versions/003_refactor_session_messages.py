"""Refactor session_messages: replace session_id FK with session_key string

Revision ID: 003
Revises: 002
Create Date: 2026-03-02

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop old index and FK, then the column
    op.drop_index("ix_session_messages_session_id", table_name="session_messages")
    op.drop_constraint(
        "session_messages_session_id_fkey", "session_messages", type_="foreignkey"
    )
    op.drop_column("session_messages", "session_id")

    # Add new session_key string column
    op.add_column(
        "session_messages",
        sa.Column("session_key", sa.String(100), nullable=False, server_default=""),
    )
    op.alter_column("session_messages", "session_key", server_default=None)
    op.create_index("ix_session_messages_session_key", "session_messages", ["session_key"])


def downgrade() -> None:
    op.drop_index("ix_session_messages_session_key", table_name="session_messages")
    op.drop_column("session_messages", "session_key")
    op.add_column(
        "session_messages",
        sa.Column("session_id", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_foreign_key(
        "session_messages_session_id_fkey",
        "session_messages",
        "sessions",
        ["session_id"],
        ["id"],
    )
    op.create_index("ix_session_messages_session_id", "session_messages", ["session_id"])
