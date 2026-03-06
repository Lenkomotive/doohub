"""Add current_node_id to pipelines

Revision ID: 009
Revises: 008
Create Date: 2026-03-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "pipelines",
        sa.Column("current_node_id", sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pipelines", "current_node_id")
