"""Add input_tokens and output_tokens to pipelines

Revision ID: 010
Revises: 009
Create Date: 2026-03-08

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("pipelines", sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("pipelines", sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("pipelines", "output_tokens")
    op.drop_column("pipelines", "input_tokens")
