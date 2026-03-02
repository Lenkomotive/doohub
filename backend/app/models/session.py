from datetime import datetime

from sqlalchemy import DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SessionMessage(Base):
    """Local cache of session messages for history.

    Sessions themselves are owned by the provider API.
    session_key references the provider session, not a local FK.
    """

    __tablename__ = "session_messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_key: Mapped[str] = mapped_column(String(100), index=True)
    role: Mapped[str] = mapped_column(String(20))  # user, assistant
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Pipeline(Base):
    """Maps to dooslave OrchestratorStore pipelines."""

    __tablename__ = "pipelines"

    id: Mapped[int] = mapped_column(primary_key=True)
    pipeline_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    repo: Mapped[str] = mapped_column(String(200))
    repo_path: Mapped[str] = mapped_column(String(500))
    issue_number: Mapped[int] = mapped_column()
    issue_title: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(
        Enum(
            "planning", "planned", "developing", "developed",
            "reviewing", "done", "failed",
            name="pipeline_status",
        ),
        default="planning",
    )
    pr_number: Mapped[int | None] = mapped_column(nullable=True)
    branch: Mapped[str | None] = mapped_column(String(200), nullable=True)
    worktree_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    review_round: Mapped[int] = mapped_column(default=0)
    claude_session_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
