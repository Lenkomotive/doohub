from datetime import datetime, timezone, timedelta

import pytest
from pydantic import ValidationError

from app.schemas.pipeline_schedule import (
    CreatePipelineScheduleRequest,
    UpdatePipelineScheduleRequest,
)


class TestCreatePipelineScheduleRequest:
    def test_valid_recurring(self):
        req = CreatePipelineScheduleRequest(
            name="Nightly build",
            repo_path="owner/repo",
            task_description="Run tests",
            schedule_type="recurring",
            cron_expression="0 0 * * *",
        )
        assert req.schedule_type == "recurring"
        assert req.cron_expression == "0 0 * * *"

    def test_valid_once(self):
        future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
        req = CreatePipelineScheduleRequest(
            name="One-off",
            repo_path="owner/repo",
            task_description="Deploy",
            schedule_type="once",
            scheduled_at=future,
        )
        assert req.schedule_type == "once"

    def test_recurring_without_cron_fails(self):
        with pytest.raises(ValidationError, match="cron_expression is required"):
            CreatePipelineScheduleRequest(
                name="Bad",
                repo_path="owner/repo",
                task_description="Fail",
                schedule_type="recurring",
            )

    def test_once_without_scheduled_at_fails(self):
        with pytest.raises(ValidationError, match="scheduled_at is required"):
            CreatePipelineScheduleRequest(
                name="Bad",
                repo_path="owner/repo",
                task_description="Fail",
                schedule_type="once",
            )

    def test_invalid_cron_expression_fails(self):
        with pytest.raises(ValidationError, match="Invalid cron expression"):
            CreatePipelineScheduleRequest(
                name="Bad",
                repo_path="owner/repo",
                task_description="Fail",
                schedule_type="recurring",
                cron_expression="not a cron",
            )

    def test_invalid_timezone_fails(self):
        with pytest.raises(ValidationError, match="Invalid timezone"):
            CreatePipelineScheduleRequest(
                name="Bad",
                repo_path="owner/repo",
                task_description="Fail",
                schedule_type="recurring",
                cron_expression="0 0 * * *",
                timezone="Fake/Nowhere",
            )

    def test_scheduled_at_in_past_fails(self):
        past = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        with pytest.raises(ValidationError, match="must be in the future"):
            CreatePipelineScheduleRequest(
                name="Bad",
                repo_path="owner/repo",
                task_description="Fail",
                schedule_type="once",
                scheduled_at=past,
            )

    def test_valid_timezone(self):
        req = CreatePipelineScheduleRequest(
            name="Berlin schedule",
            repo_path="owner/repo",
            task_description="Run",
            schedule_type="recurring",
            cron_expression="0 9 * * 1-5",
            timezone="Europe/Berlin",
        )
        assert req.timezone == "Europe/Berlin"


class TestUpdatePipelineScheduleRequest:
    def test_all_optional(self):
        req = UpdatePipelineScheduleRequest()
        assert req.name is None
        assert req.cron_expression is None

    def test_invalid_cron_on_update(self):
        with pytest.raises(ValidationError, match="Invalid cron expression"):
            UpdatePipelineScheduleRequest(cron_expression="bad cron")

    def test_invalid_timezone_on_update(self):
        with pytest.raises(ValidationError, match="Invalid timezone"):
            UpdatePipelineScheduleRequest(timezone="Nope/Nope")

    def test_valid_partial_update(self):
        req = UpdatePipelineScheduleRequest(name="New name", skip_if_running=False)
        assert req.name == "New name"
        assert req.skip_if_running is False
