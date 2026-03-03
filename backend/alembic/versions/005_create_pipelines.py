"""Create pipelines table

Revision ID: 005
Revises: 004
Create Date: 2026-03-03

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipelines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("pipeline_key", sa.String(100), unique=True, nullable=False, index=True),
        sa.Column("repo_path", sa.String(500), nullable=False),
        sa.Column("issue_number", sa.Integer(), nullable=True),
        sa.Column("issue_title", sa.String(500), nullable=True),
        sa.Column("task_description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="planning"),
        sa.Column("plan", sa.Text(), nullable=True),
        sa.Column("branch", sa.String(200), nullable=True),
        sa.Column("pr_number", sa.Integer(), nullable=True),
        sa.Column("pr_url", sa.String(500), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("review_round", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("model", sa.String(50), nullable=False, server_default="claude-sonnet-4-6"),
        sa.Column("total_cost_usd", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("claude_session_id", sa.String(200), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("pipelines")
