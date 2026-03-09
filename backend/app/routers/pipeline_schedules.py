import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as DBSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.schedule_poller import compute_next_run
from app.models.pipeline import Pipeline
from app.models.pipeline_schedule import PipelineSchedule
from app.models.user import User
from app.schemas.pipeline_schedule import (
    CreatePipelineScheduleRequest,
    UpdatePipelineScheduleRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pipeline_schedules"])

UPDATABLE_FIELDS = {
    "name", "repo_path", "issue_number", "task_description", "model",
    "template_id", "cron_expression", "scheduled_at", "timezone",
    "skip_if_running", "is_active",
}


def _serialize(s: PipelineSchedule) -> dict:
    return {
        "id": s.id,
        "name": s.name,
        "repo_path": s.repo_path,
        "issue_number": s.issue_number,
        "task_description": s.task_description,
        "model": s.model,
        "template_id": s.template_id,
        "schedule_type": s.schedule_type,
        "cron_expression": s.cron_expression,
        "scheduled_at": s.scheduled_at.isoformat() if s.scheduled_at else None,
        "timezone": s.timezone,
        "is_active": s.is_active,
        "skip_if_running": s.skip_if_running,
        "next_run_at": s.next_run_at.isoformat() if s.next_run_at else None,
        "last_run_at": s.last_run_at.isoformat() if s.last_run_at else None,
        "run_count": s.run_count,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


def _get_user_schedule(db: DBSession, schedule_id: int, user_id: int) -> PipelineSchedule:
    schedule = db.query(PipelineSchedule).filter(
        PipelineSchedule.id == schedule_id, PipelineSchedule.user_id == user_id
    ).first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


@router.post("/pipeline-schedules", status_code=201)
async def create_schedule(
    body: CreatePipelineScheduleRequest,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    schedule = PipelineSchedule(
        user_id=user.id,
        name=body.name,
        repo_path=body.repo_path,
        issue_number=body.issue_number,
        task_description=body.task_description,
        model=body.model,
        template_id=body.template_id,
        schedule_type=body.schedule_type,
        cron_expression=body.cron_expression,
        scheduled_at=datetime.fromisoformat(body.scheduled_at) if body.scheduled_at else None,
        timezone=body.timezone,
        skip_if_running=body.skip_if_running,
    )

    # Compute next_run_at
    if body.schedule_type == "once":
        schedule.next_run_at = datetime.fromisoformat(body.scheduled_at)
    else:
        schedule.next_run_at = compute_next_run(body.cron_expression, body.timezone)

    db.add(schedule)
    db.commit()
    db.refresh(schedule)
    return _serialize(schedule)


@router.get("/pipeline-schedules")
async def list_schedules(
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    schedules = (
        db.query(PipelineSchedule)
        .filter(PipelineSchedule.user_id == user.id)
        .order_by(PipelineSchedule.created_at.desc())
        .all()
    )
    return {"schedules": [_serialize(s) for s in schedules], "total": len(schedules)}


@router.get("/pipeline-schedules/{schedule_id}")
async def get_schedule(
    schedule_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return _serialize(_get_user_schedule(db, schedule_id, user.id))


@router.patch("/pipeline-schedules/{schedule_id}")
async def update_schedule(
    schedule_id: int,
    body: UpdatePipelineScheduleRequest,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    schedule = _get_user_schedule(db, schedule_id, user.id)
    update_data = body.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field in UPDATABLE_FIELDS:
            if field == "scheduled_at" and value is not None:
                value = datetime.fromisoformat(value)
            setattr(schedule, field, value)

    # Recompute next_run_at if schedule params changed
    needs_recompute = any(k in update_data for k in ("cron_expression", "timezone", "scheduled_at", "is_active"))
    if needs_recompute and schedule.is_active:
        if schedule.schedule_type == "once" and schedule.scheduled_at:
            schedule.next_run_at = schedule.scheduled_at
        elif schedule.schedule_type == "recurring" and schedule.cron_expression:
            schedule.next_run_at = compute_next_run(schedule.cron_expression, schedule.timezone)

    db.commit()
    db.refresh(schedule)
    return _serialize(schedule)


@router.delete("/pipeline-schedules/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    schedule = _get_user_schedule(db, schedule_id, user.id)
    # Nullify schedule_id on linked pipelines
    db.query(Pipeline).filter(Pipeline.schedule_id == schedule.id).update(
        {"schedule_id": None}, synchronize_session=False
    )
    db.delete(schedule)
    db.commit()


@router.post("/pipeline-schedules/{schedule_id}/pause")
async def pause_schedule(
    schedule_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    schedule = _get_user_schedule(db, schedule_id, user.id)
    schedule.is_active = False
    schedule.next_run_at = None
    db.commit()
    db.refresh(schedule)
    return _serialize(schedule)


@router.post("/pipeline-schedules/{schedule_id}/resume")
async def resume_schedule(
    schedule_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    schedule = _get_user_schedule(db, schedule_id, user.id)

    if schedule.schedule_type == "once":
        if not schedule.scheduled_at or schedule.scheduled_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Cannot resume a one-off schedule with a past time")
        schedule.next_run_at = schedule.scheduled_at
    else:
        schedule.next_run_at = compute_next_run(schedule.cron_expression, schedule.timezone)

    schedule.is_active = True
    db.commit()
    db.refresh(schedule)
    return _serialize(schedule)


@router.get("/pipeline-schedules/{schedule_id}/history")
async def schedule_history(
    schedule_id: int,
    limit: int = Query(default=20, le=100),
    offset: int = Query(default=0, ge=0),
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    _get_user_schedule(db, schedule_id, user.id)  # auth check
    pipelines = (
        db.query(Pipeline)
        .filter(Pipeline.schedule_id == schedule_id)
        .order_by(Pipeline.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    total = db.query(Pipeline).filter(Pipeline.schedule_id == schedule_id).count()
    return {
        "pipelines": [
            {
                "pipeline_key": p.pipeline_key,
                "status": p.status,
                "created_at": p.created_at.isoformat(),
                "error": p.error,
            }
            for p in pipelines
        ],
        "total": total,
    }
