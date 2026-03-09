from datetime import datetime, timezone

from croniter import croniter
from pydantic import BaseModel, model_validator


class CreatePipelineScheduleRequest(BaseModel):
    name: str
    repo_path: str
    issue_number: int | None = None
    task_description: str | None = None
    model: str = "claude-opus-4-6"
    template_id: int | None = None
    schedule_type: str  # "once" or "recurring"
    cron_expression: str | None = None
    scheduled_at: str | None = None  # ISO 8601
    timezone: str = "UTC"
    skip_if_running: bool = True

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.schedule_type not in ("once", "recurring"):
            raise ValueError('schedule_type must be "once" or "recurring"')
        if self.schedule_type == "recurring":
            if not self.cron_expression:
                raise ValueError("cron_expression is required for recurring schedules")
            if not croniter.is_valid(self.cron_expression):
                raise ValueError(f"Invalid cron expression: {self.cron_expression}")
        if self.schedule_type == "once":
            if not self.scheduled_at:
                raise ValueError("scheduled_at is required for one-off schedules")
            dt = datetime.fromisoformat(self.scheduled_at)
            if dt.tzinfo is None:
                raise ValueError("scheduled_at must include timezone info")
            if dt < datetime.now(timezone.utc):
                raise ValueError("scheduled_at must be in the future")
        return self


class UpdatePipelineScheduleRequest(BaseModel):
    name: str | None = None
    repo_path: str | None = None
    issue_number: int | None = None
    task_description: str | None = None
    model: str | None = None
    template_id: int | None = None
    cron_expression: str | None = None
    scheduled_at: str | None = None
    timezone: str | None = None
    skip_if_running: bool | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def validate_update(self):
        if self.cron_expression is not None and not croniter.is_valid(self.cron_expression):
            raise ValueError(f"Invalid cron expression: {self.cron_expression}")
        if self.scheduled_at is not None:
            dt = datetime.fromisoformat(self.scheduled_at)
            if dt.tzinfo is None:
                raise ValueError("scheduled_at must include timezone info")
        return self
