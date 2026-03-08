from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from croniter import croniter
from pydantic import BaseModel, model_validator


class CreatePipelineScheduleRequest(BaseModel):
    name: str
    repo_path: str
    issue_number: int | None = None
    task_description: str
    model: str = "claude-opus-4-6"
    template_id: int | None = None
    schedule_type: Literal["once", "recurring"]
    cron_expression: str | None = None
    scheduled_at: str | None = None  # ISO 8601
    timezone: str = "UTC"
    skip_if_running: bool = True

    @model_validator(mode="after")
    def validate_schedule(self):
        # Validate timezone
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, KeyError):
            raise ValueError(f"Invalid timezone: {self.timezone}")

        if self.schedule_type == "recurring":
            if not self.cron_expression:
                raise ValueError("cron_expression is required for recurring schedules")
            if not croniter.is_valid(self.cron_expression):
                raise ValueError(f"Invalid cron expression: {self.cron_expression}")
        elif self.schedule_type == "once":
            if not self.scheduled_at:
                raise ValueError("scheduled_at is required for one-off schedules")
            from datetime import datetime, timezone as tz
            try:
                dt = datetime.fromisoformat(self.scheduled_at)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz.utc)
                if dt <= datetime.now(tz.utc):
                    raise ValueError("scheduled_at must be in the future")
            except (ValueError, TypeError) as e:
                if "must be in the future" in str(e):
                    raise
                raise ValueError(f"Invalid scheduled_at datetime: {self.scheduled_at}")
        return self


class UpdatePipelineScheduleRequest(BaseModel):
    name: str | None = None
    repo_path: str | None = None
    issue_number: int | None = None
    task_description: str | None = None
    model: str | None = None
    template_id: int | None = None
    schedule_type: Literal["once", "recurring"] | None = None
    cron_expression: str | None = None
    scheduled_at: str | None = None
    timezone: str | None = None
    skip_if_running: bool | None = None

    @model_validator(mode="after")
    def validate_schedule(self):
        if self.timezone is not None:
            try:
                ZoneInfo(self.timezone)
            except (ZoneInfoNotFoundError, KeyError):
                raise ValueError(f"Invalid timezone: {self.timezone}")

        if self.cron_expression is not None:
            if not croniter.is_valid(self.cron_expression):
                raise ValueError(f"Invalid cron expression: {self.cron_expression}")

        if self.scheduled_at is not None:
            from datetime import datetime, timezone as tz
            try:
                dt = datetime.fromisoformat(self.scheduled_at)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=tz.utc)
                if dt <= datetime.now(tz.utc):
                    raise ValueError("scheduled_at must be in the future")
            except (ValueError, TypeError) as e:
                if "must be in the future" in str(e):
                    raise
                raise ValueError(f"Invalid scheduled_at datetime: {self.scheduled_at}")
        return self


class PipelineScheduleResponse(BaseModel):
    id: int
    name: str
    repo_path: str
    issue_number: int | None
    task_description: str
    model: str
    template_id: int | None
    schedule_type: str
    cron_expression: str | None
    scheduled_at: str | None
    timezone: str
    is_active: bool
    skip_if_running: bool
    next_run_at: str | None
    last_run_at: str | None
    created_at: str
    updated_at: str
