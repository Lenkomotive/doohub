"""Create pipeline_schedules table and add schedule_id to pipelines

Revision ID: 010
Revises: 009
Create Date: 2026-03-09

"""
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "pipeline_schedules",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("repo_path", sa.String(500), nullable=False),
        sa.Column("issue_number", sa.Integer(), nullable=True),
        sa.Column("task_description", sa.Text(), nullable=True),
        sa.Column("model", sa.String(50), nullable=False, server_default="claude-opus-4-6"),
        sa.Column(
            "template_id",
            sa.Integer(),
            sa.ForeignKey("pipeline_templates.id"),
            nullable=True,
        ),
        sa.Column("schedule_type", sa.String(20), nullable=False),  # "once" or "recurring"
        sa.Column("cron_expression", sa.String(100), nullable=True),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(50), nullable=False, server_default="UTC"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("skip_if_running", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("run_count", sa.Integer(), nullable=False, server_default="0"),
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
    op.create_index(
        "ix_pipeline_schedules_active_next_run",
        "pipeline_schedules",
        ["is_active", "next_run_at"],
    )
    op.add_column(
        "pipelines",
        sa.Column(
            "schedule_id",
            sa.Integer(),
            sa.ForeignKey("pipeline_schedules.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("pipelines", "schedule_id")
    op.drop_index("ix_pipeline_schedules_active_next_run", table_name="pipeline_schedules")
    op.drop_table("pipeline_schedules")
