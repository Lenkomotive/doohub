"""Create sessions, session_messages, and pipelines tables

Revision ID: 002
Revises: 001
Create Date: 2026-03-01

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_key", sa.String(100), unique=True, nullable=False),
        sa.Column(
            "status",
            sa.Enum("idle", "busy", name="session_status"),
            nullable=False,
            server_default="idle",
        ),
        sa.Column("model", sa.String(50), nullable=False, server_default="sonnet"),
        sa.Column("project_path", sa.String(500), nullable=False),
        sa.Column("claude_session_id", sa.String(100), nullable=True),
        sa.Column("interactive", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_sessions_session_key", "sessions", ["session_key"])

    op.create_table(
        "session_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "session_id", sa.Integer(), sa.ForeignKey("sessions.id"), nullable=False,
        ),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_session_messages_session_id", "session_messages", ["session_id"])

    op.create_table(
        "pipelines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("pipeline_key", sa.String(100), unique=True, nullable=False),
        sa.Column("repo", sa.String(200), nullable=False),
        sa.Column("repo_path", sa.String(500), nullable=False),
        sa.Column("issue_number", sa.Integer(), nullable=False),
        sa.Column("issue_title", sa.String(500), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "planning", "planned", "developing", "developed",
                "reviewing", "done", "failed",
                name="pipeline_status",
            ),
            nullable=False,
            server_default="planning",
        ),
        sa.Column("pr_number", sa.Integer(), nullable=True),
        sa.Column("branch", sa.String(200), nullable=True),
        sa.Column("worktree_path", sa.String(500), nullable=True),
        sa.Column("review_round", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("claude_session_id", sa.String(100), nullable=True),
        sa.Column("plan", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column(
            "started_at",
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
    op.create_index("ix_pipelines_pipeline_key", "pipelines", ["pipeline_key"])


def downgrade() -> None:
    op.drop_table("session_messages")
    op.drop_table("sessions")
    op.drop_table("pipelines")
    op.execute("DROP TYPE IF EXISTS session_status")
    op.execute("DROP TYPE IF EXISTS pipeline_status")
