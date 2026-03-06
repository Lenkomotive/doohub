from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Pipeline(Base):
    __tablename__ = "pipelines"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    pipeline_key: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    repo_path: Mapped[str] = mapped_column(String(500))
    issue_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    issue_title: Mapped[str | None] = mapped_column(String(500), nullable=True)
    task_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="planning")
    plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    branch: Mapped[str | None] = mapped_column(String(200), nullable=True)
    pr_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    pr_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    review_round: Mapped[int] = mapped_column(Integer, default=0)
    model: Mapped[str] = mapped_column(String(50), default="claude-opus-4-6")
    total_cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    claude_session_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    step_logs: Mapped[list | None] = mapped_column(JSONB, nullable=True, default=list)
    current_node_id: Mapped[str | None] = mapped_column(String(200), nullable=True)
    template_id: Mapped[int | None] = mapped_column(
        ForeignKey("pipeline_templates.id"), nullable=True
    )
    template = relationship("PipelineTemplate", lazy="joined")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
