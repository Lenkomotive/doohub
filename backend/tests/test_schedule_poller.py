from datetime import datetime, timezone, timedelta
from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from app.core.schedule_poller import compute_next_run, _poll_once, _execute_schedule


class TestComputeNextRun:
    def test_every_minute(self):
        result = compute_next_run("* * * * *", "UTC")
        assert result.tzinfo is not None
        # Should be within ~60s from now
        diff = (result - datetime.now(timezone.utc)).total_seconds()
        assert 0 < diff <= 61

    def test_daily_midnight(self):
        result = compute_next_run("0 0 * * *", "UTC")
        assert result.hour == 0
        assert result.minute == 0

    def test_timezone_aware(self):
        utc_result = compute_next_run("0 9 * * *", "UTC")
        berlin_result = compute_next_run("0 9 * * *", "Europe/Berlin")
        # 9 AM Berlin != 9 AM UTC (offset is 1 or 2 hours)
        assert utc_result != berlin_result

    def test_returns_utc(self):
        result = compute_next_run("0 12 * * *", "America/New_York")
        assert result.tzinfo == timezone.utc


class TestPollOnce:
    @pytest.mark.asyncio
    @patch("app.core.schedule_poller.SessionLocal")
    @patch("app.core.schedule_poller._execute_schedule", new_callable=AsyncMock)
    async def test_picks_up_due_schedule(self, mock_execute, mock_session_cls):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        schedule = MagicMock()
        schedule.id = 1
        schedule.is_active = True
        schedule.next_run_at = datetime.now(timezone.utc) - timedelta(minutes=1)

        mock_db.query.return_value.filter.return_value.all.return_value = [schedule]

        await _poll_once()

        mock_execute.assert_called_once()
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.schedule_poller.SessionLocal")
    @patch("app.core.schedule_poller._execute_schedule", new_callable=AsyncMock)
    async def test_skips_no_due_schedules(self, mock_execute, mock_session_cls):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db
        mock_db.query.return_value.filter.return_value.all.return_value = []

        await _poll_once()

        mock_execute.assert_not_called()
        mock_db.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.schedule_poller.SessionLocal")
    @patch("app.core.schedule_poller._execute_schedule", new_callable=AsyncMock)
    async def test_execute_error_does_not_crash(self, mock_execute, mock_session_cls):
        mock_db = MagicMock()
        mock_session_cls.return_value = mock_db

        schedule = MagicMock()
        schedule.id = 1
        mock_db.query.return_value.filter.return_value.all.return_value = [schedule]
        mock_execute.side_effect = Exception("boom")

        # Should not raise
        await _poll_once()
        mock_db.close.assert_called_once()


class TestExecuteSchedule:
    @pytest.mark.asyncio
    @patch("app.core.schedule_poller.slave", new_callable=MagicMock)
    async def test_one_off_deactivates_after_run(self, mock_slave):
        mock_slave.start_pipeline = AsyncMock()
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None  # no template

        schedule = MagicMock()
        schedule.id = 1
        schedule.schedule_type = "once"
        schedule.skip_if_running = False
        schedule.template_id = None
        schedule.user_id = 1
        schedule.repo_path = "owner/repo"
        schedule.issue_number = None
        schedule.task_description = "test"
        schedule.model = "claude-opus-4-6"
        schedule.cron_expression = None
        schedule.timezone = "UTC"

        now = datetime.now(timezone.utc)
        await _execute_schedule(db, schedule, now)

        assert schedule.is_active is False
        assert schedule.next_run_at is None
        assert schedule.last_run_at == now
        db.commit.assert_called()
        mock_slave.start_pipeline.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.schedule_poller.slave", new_callable=MagicMock)
    @patch("app.core.schedule_poller.compute_next_run")
    async def test_recurring_advances_next_run(self, mock_compute, mock_slave):
        mock_slave.start_pipeline = AsyncMock()
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_compute.return_value = future
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = None  # no template

        schedule = MagicMock()
        schedule.id = 1
        schedule.schedule_type = "recurring"
        schedule.skip_if_running = False
        schedule.template_id = None
        schedule.user_id = 1
        schedule.repo_path = "owner/repo"
        schedule.issue_number = None
        schedule.task_description = "test"
        schedule.model = "claude-opus-4-6"
        schedule.cron_expression = "0 * * * *"
        schedule.timezone = "UTC"

        now = datetime.now(timezone.utc)
        await _execute_schedule(db, schedule, now)

        assert schedule.next_run_at == future
        assert schedule.last_run_at == now
        mock_slave.start_pipeline.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.core.schedule_poller.slave", new_callable=MagicMock)
    @patch("app.core.schedule_poller.compute_next_run")
    async def test_skip_if_running_skips(self, mock_compute, mock_slave):
        mock_slave.start_pipeline = AsyncMock()
        future = datetime.now(timezone.utc) + timedelta(hours=1)
        mock_compute.return_value = future
        db = MagicMock()

        running_pipeline = MagicMock()
        # First query returns running pipeline (skip_if_running check)
        db.query.return_value.filter.return_value.first.return_value = running_pipeline

        schedule = MagicMock()
        schedule.id = 1
        schedule.schedule_type = "recurring"
        schedule.skip_if_running = True
        schedule.cron_expression = "0 * * * *"
        schedule.timezone = "UTC"

        now = datetime.now(timezone.utc)
        await _execute_schedule(db, schedule, now)

        # Pipeline should NOT have been started
        mock_slave.start_pipeline.assert_not_called()
        # next_run_at should still advance
        assert schedule.next_run_at == future
        db.commit.assert_called()
