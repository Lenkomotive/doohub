"""Create pipeline_templates table and add template_id to pipelines

Revision ID: 008
Revises: 007
Create Date: 2026-03-06

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipeline_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(200), unique=True, nullable=False),
        sa.Column("description", sa.String(500), nullable=True),
        sa.Column("definition", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.add_column(
        "pipelines",
        sa.Column("template_id", sa.Integer(), sa.ForeignKey("pipeline_templates.id"), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("pipelines", "template_id")
    op.drop_table("pipeline_templates")
