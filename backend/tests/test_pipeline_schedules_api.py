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

    def test_resume(self, client, db, test_user):
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
