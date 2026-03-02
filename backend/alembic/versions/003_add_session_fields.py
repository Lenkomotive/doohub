"""Add project_path, model, interactive, claude_session_id to sessions

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
    op.add_column("sessions", sa.Column("project_path", sa.String(500), nullable=False, server_default=""))
    op.add_column("sessions", sa.Column("model", sa.String(50), nullable=False, server_default="claude-opus-4-6"))
    op.add_column("sessions", sa.Column("interactive", sa.Boolean(), nullable=False, server_default="false"))
    op.add_column("sessions", sa.Column("claude_session_id", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("sessions", "claude_session_id")
    op.drop_column("sessions", "interactive")
    op.drop_column("sessions", "model")
    op.drop_column("sessions", "project_path")
