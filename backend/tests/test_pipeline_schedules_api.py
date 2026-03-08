from datetime import datetime, timezone, timedelta

import pytest

from app.models.pipeline import Pipeline
from app.models.pipeline_schedule import PipelineSchedule


class TestCreateSchedule:
    def test_create_recurring(self, client, db):
        resp = client.post("/pipeline-schedules", json={
            "name": "Nightly",
            "repo_path": "owner/repo",
            "task_description": "Run nightly tests",
            "schedule_type": "recurring",
            "cron_expression": "0 0 * * *",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Nightly"
        assert data["schedule_type"] == "recurring"
        assert data["cron_expression"] == "0 0 * * *"
        assert data["is_active"] is True
        assert data["next_run_at"] is not None

    def test_create_once(self, client, db):
        future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        resp = client.post("/pipeline-schedules", json={
            "name": "One-off deploy",
            "repo_path": "owner/repo",
            "task_description": "Deploy to prod",
            "schedule_type": "once",
            "scheduled_at": future,
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["schedule_type"] == "once"
        assert data["next_run_at"] is not None

    def test_create_invalid_cron(self, client, db):
        resp = client.post("/pipeline-schedules", json={
            "name": "Bad",
            "repo_path": "owner/repo",
            "task_description": "Fail",
            "schedule_type": "recurring",
            "cron_expression": "not valid",
        })
        assert resp.status_code == 422


class TestListSchedules:
    def test_list_empty(self, client, db):
        resp = client.get("/pipeline-schedules")
        assert resp.status_code == 200
        assert resp.json()["schedules"] == []
        assert resp.json()["total"] == 0

    def test_list_returns_user_schedules(self, client, db, test_user):
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="Test",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="recurring",
            cron_expression="0 * * * *",
            timezone="UTC",
        )
        db.add(schedule)
        db.commit()

        resp = client.get("/pipeline-schedules")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1


class TestGetSchedule:
    def test_get_existing(self, client, db, test_user):
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="Test",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="recurring",
            cron_expression="0 * * * *",
            timezone="UTC",
        )
        db.add(schedule)
        db.commit()

        resp = client.get(f"/pipeline-schedules/{schedule.id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Test"

    def test_get_nonexistent(self, client, db):
        resp = client.get("/pipeline-schedules/999")
        assert resp.status_code == 404


class TestUpdateSchedule:
    def test_update_name(self, client, db, test_user):
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="Old",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="recurring",
            cron_expression="0 * * * *",
            timezone="UTC",
        )
        db.add(schedule)
        db.commit()

        resp = client.put(f"/pipeline-schedules/{schedule.id}", json={"name": "New"})
        assert resp.status_code == 200
        assert resp.json()["name"] == "New"

    def test_update_nonexistent(self, client, db):
        resp = client.put("/pipeline-schedules/999", json={"name": "New"})
        assert resp.status_code == 404

    def test_change_schedule_type_to_once_without_scheduled_at_fails(self, client, db, test_user):
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="Recurring",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="recurring",
            cron_expression="0 * * * *",
            timezone="UTC",
        )
        db.add(schedule)
        db.commit()

        resp = client.put(
            f"/pipeline-schedules/{schedule.id}",
            json={"schedule_type": "once"},
        )
        assert resp.status_code == 422

    def test_change_schedule_type_to_recurring_without_cron_fails(self, client, db, test_user):
        future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="Once",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="once",
            scheduled_at=datetime.now(timezone.utc) + timedelta(hours=2),
            timezone="UTC",
        )
        db.add(schedule)
        db.commit()

        resp = client.put(
            f"/pipeline-schedules/{schedule.id}",
            json={"schedule_type": "recurring"},
        )
        assert resp.status_code == 422

    def test_change_schedule_type_to_once_with_scheduled_at_succeeds(self, client, db, test_user):
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="Recurring",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="recurring",
            cron_expression="0 * * * *",
            timezone="UTC",
        )
        db.add(schedule)
        db.commit()

        future = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
        resp = client.put(
            f"/pipeline-schedules/{schedule.id}",
            json={"schedule_type": "once", "scheduled_at": future},
        )
        assert resp.status_code == 200
        assert resp.json()["schedule_type"] == "once"


class TestDeleteSchedule:
    def test_delete_existing(self, client, db, test_user):
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="Delete me",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="recurring",
            cron_expression="0 * * * *",
            timezone="UTC",
        )
        db.add(schedule)
        db.commit()

        resp = client.delete(f"/pipeline-schedules/{schedule.id}")
        assert resp.status_code == 204

        assert db.query(PipelineSchedule).filter_by(id=schedule.id).first() is None

    def test_delete_nonexistent(self, client, db):
        resp = client.delete("/pipeline-schedules/999")
        assert resp.status_code == 404

    def test_delete_with_linked_pipelines(self, client, db, test_user):
        """Deleting a schedule with linked pipelines should succeed (SET NULL)."""
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="Has history",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="recurring",
            cron_expression="0 * * * *",
            timezone="UTC",
        )
        db.add(schedule)
        db.commit()

        pipeline = Pipeline(
            user_id=test_user.id,
            pipeline_key="linked001",
            repo_path="owner/repo",
            task_description="test",
            schedule_id=schedule.id,
        )
        db.add(pipeline)
        db.commit()

        resp = client.delete(f"/pipeline-schedules/{schedule.id}")
        assert resp.status_code == 204

        # Pipeline should still exist with schedule_id set to NULL
        db.expire_all()
        remaining = db.query(Pipeline).filter_by(pipeline_key="linked001").first()
        assert remaining is not None
        assert remaining.schedule_id is None


class TestPauseResume:
    def test_pause(self, client, db, test_user):
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="Pausable",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="recurring",
            cron_expression="0 * * * *",
            timezone="UTC",
            is_active=True,
        )
        db.add(schedule)
        db.commit()

        resp = client.post(f"/pipeline-schedules/{schedule.id}/pause")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is False

    def test_resume_recurring(self, client, db, test_user):
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="Resumable",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="recurring",
            cron_expression="0 * * * *",
            timezone="UTC",
            is_active=False,
        )
        db.add(schedule)
        db.commit()

        resp = client.post(f"/pipeline-schedules/{schedule.id}/resume")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True
        assert resp.json()["next_run_at"] is not None

    def test_resume_once_with_past_scheduled_at_fails(self, client, db, test_user):
        """Resuming a one-off schedule whose scheduled_at is in the past should fail."""
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="Past once",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="once",
            scheduled_at=datetime.now(timezone.utc) - timedelta(hours=1),
            timezone="UTC",
            is_active=False,
        )
        db.add(schedule)
        db.commit()

        resp = client.post(f"/pipeline-schedules/{schedule.id}/resume")
        assert resp.status_code == 409
        assert "past" in resp.json()["detail"].lower()

    def test_resume_once_with_future_scheduled_at_succeeds(self, client, db, test_user):
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="Future once",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="once",
            scheduled_at=future,
            timezone="UTC",
            is_active=False,
        )
        db.add(schedule)
        db.commit()

        resp = client.post(f"/pipeline-schedules/{schedule.id}/resume")
        assert resp.status_code == 200
        assert resp.json()["is_active"] is True


class TestScheduleHistory:
    def test_history_empty(self, client, db, test_user):
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="History test",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="recurring",
            cron_expression="0 * * * *",
            timezone="UTC",
        )
        db.add(schedule)
        db.commit()

        resp = client.get(f"/pipeline-schedules/{schedule.id}/history")
        assert resp.status_code == 200
        assert resp.json()["pipelines"] == []
        assert resp.json()["total"] == 0

    def test_history_returns_linked_pipelines(self, client, db, test_user):
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="History test",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="recurring",
            cron_expression="0 * * * *",
            timezone="UTC",
        )
        db.add(schedule)
        db.commit()

        pipeline = Pipeline(
            user_id=test_user.id,
            pipeline_key="abc123",
            repo_path="owner/repo",
            task_description="test",
            schedule_id=schedule.id,
        )
        db.add(pipeline)
        db.commit()

        resp = client.get(f"/pipeline-schedules/{schedule.id}/history")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["pipelines"][0]["pipeline_key"] == "abc123"

    def test_history_pagination(self, client, db, test_user):
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="Paginated",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="recurring",
            cron_expression="0 * * * *",
            timezone="UTC",
        )
        db.add(schedule)
        db.commit()

        for i in range(5):
            db.add(Pipeline(
                user_id=test_user.id,
                pipeline_key=f"key{i:03d}",
                repo_path="owner/repo",
                task_description="test",
                schedule_id=schedule.id,
            ))
        db.commit()

        resp = client.get(f"/pipeline-schedules/{schedule.id}/history?limit=2&offset=0")
        assert resp.status_code == 200
        assert len(resp.json()["pipelines"]) == 2
        assert resp.json()["total"] == 5

    def test_history_limit_bounded(self, client, db, test_user):
        """Limit is bounded to 100 max."""
        schedule = PipelineSchedule(
            user_id=test_user.id,
            name="Bounded",
            repo_path="owner/repo",
            task_description="test",
            schedule_type="recurring",
            cron_expression="0 * * * *",
            timezone="UTC",
        )
        db.add(schedule)
        db.commit()

        resp = client.get(f"/pipeline-schedules/{schedule.id}/history?limit=200")
        assert resp.status_code == 422
