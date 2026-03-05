"""Add notification preferences to users

Revision ID: 007
Revises: 006
Create Date: 2026-03-05

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("notify_sessions", sa.Boolean(), server_default="true", nullable=False))
    op.add_column("users", sa.Column("notify_pipelines", sa.Boolean(), server_default="true", nullable=False))


def downgrade() -> None:
    op.drop_column("users", "notify_pipelines")
    op.drop_column("users", "notify_sessions")
