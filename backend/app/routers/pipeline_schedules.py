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
    UPDATABLE_FIELDS,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pipeline-schedules"])


@router.post("/pipeline-schedules", status_code=201)
async def create_schedule(
    body: CreatePipelineScheduleRequest,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Compute next_run_at
    if body.schedule_type == "recurring":
        next_run_at = compute_next_run(body.cron_expression, body.timezone)
    else:
        dt = datetime.fromisoformat(body.scheduled_at)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        next_run_at = dt.astimezone(timezone.utc)

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
        scheduled_at=next_run_at if body.schedule_type == "once" else None,
        timezone=body.timezone,
        skip_if_running=body.skip_if_running,
        next_run_at=next_run_at,
    )
    db.add(schedule)
    db.commit()
    db.refresh(schedule)

    return _serialize_schedule(schedule)


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
    return {
        "schedules": [_serialize_schedule(s) for s in schedules],
        "total": len(schedules),
    }


@router.get("/pipeline-schedules/{schedule_id}")
async def get_schedule(
    schedule_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    schedule = _get_user_schedule(db, schedule_id, user.id)
    return _serialize_schedule(schedule)


@router.put("/pipeline-schedules/{schedule_id}")
async def update_schedule(
    schedule_id: int,
    body: UpdatePipelineScheduleRequest,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    schedule = _get_user_schedule(db, schedule_id, user.id)

    update_data = body.model_dump(exclude_unset=True)
    schedule_params_changed = False

    for field, value in update_data.items():
        # Only allow known updatable fields
        if field not in UPDATABLE_FIELDS:
            continue

        if field == "scheduled_at" and value is not None:
            dt = datetime.fromisoformat(value)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            setattr(schedule, field, dt.astimezone(timezone.utc))
        else:
            setattr(schedule, field, value)

        if field in ("cron_expression", "scheduled_at", "timezone", "schedule_type"):
            schedule_params_changed = True

    # Recompute next_run_at if schedule params changed
    if schedule_params_changed:
        if schedule.schedule_type == "recurring" and schedule.cron_expression:
            schedule.next_run_at = compute_next_run(
                schedule.cron_expression, schedule.timezone
            )
        elif schedule.schedule_type == "once" and schedule.scheduled_at:
            schedule.next_run_at = schedule.scheduled_at

    db.commit()
    db.refresh(schedule)

    return _serialize_schedule(schedule)


@router.delete("/pipeline-schedules/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    schedule = _get_user_schedule(db, schedule_id, user.id)
    # Nullify schedule_id on linked pipelines before deleting
    db.query(Pipeline).filter(Pipeline.schedule_id == schedule.id).update(
        {"schedule_id": None}, synchronize_session="fetch"
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
    db.commit()
    return _serialize_schedule(schedule)


@router.post("/pipeline-schedules/{schedule_id}/resume")
async def resume_schedule(
    schedule_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    schedule = _get_user_schedule(db, schedule_id, user.id)

    # Recompute next_run_at
    if schedule.schedule_type == "recurring" and schedule.cron_expression:
        next_run = compute_next_run(schedule.cron_expression, schedule.timezone)
    elif schedule.schedule_type == "once" and schedule.scheduled_at:
        scheduled_at = schedule.scheduled_at
        if scheduled_at.tzinfo is None:
            scheduled_at = scheduled_at.replace(tzinfo=timezone.utc)
        if scheduled_at <= datetime.now(timezone.utc):
            raise HTTPException(
                status_code=409,
                detail="Cannot resume: scheduled_at is in the past. Update scheduled_at first.",
            )
        next_run = scheduled_at
    else:
        raise HTTPException(
            status_code=409,
            detail="Cannot resume: schedule has no valid timing configuration.",
        )

    schedule.is_active = True
    schedule.next_run_at = next_run
    db.commit()
    db.refresh(schedule)

    return _serialize_schedule(schedule)


@router.get("/pipeline-schedules/{schedule_id}/history")
async def schedule_history(
    schedule_id: int,
    limit: int = Query(default=20, le=100, ge=1),
    offset: int = Query(default=0, ge=0),
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Verify ownership
    _get_user_schedule(db, schedule_id, user.id)

    query = (
        db.query(Pipeline)
        .filter(Pipeline.schedule_id == schedule_id)
        .order_by(Pipeline.created_at.desc())
    )
    total = query.count()
    pipelines = query.offset(offset).limit(limit).all()

    return {
        "pipelines": [_serialize_pipeline(p) for p in pipelines],
        "total": total,
    }


# --- helpers ---


def _get_user_schedule(
    db: DBSession, schedule_id: int, user_id: int
) -> PipelineSchedule:
    schedule = (
        db.query(PipelineSchedule)
        .filter(PipelineSchedule.id == schedule_id, PipelineSchedule.user_id == user_id)
        .first()
    )
    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")
    return schedule


def _serialize_schedule(s: PipelineSchedule) -> dict:
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
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


def _serialize_pipeline(p: Pipeline) -> dict:
    return {
        "pipeline_key": p.pipeline_key,
        "repo_path": p.repo_path,
        "issue_number": p.issue_number,
        "issue_title": p.issue_title,
        "task_description": p.task_description,
        "status": p.status,
        "model": p.model,
        "total_cost_usd": p.total_cost_usd,
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }
