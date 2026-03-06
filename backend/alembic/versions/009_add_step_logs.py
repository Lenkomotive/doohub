"""Add step_logs to pipelines

Revision ID: 009
Revises: 008
Create Date: 2026-03-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pipelines", sa.Column("step_logs", postgresql.JSONB(), nullable=True))


def downgrade() -> None:
    op.drop_column("pipelines", "step_logs")
