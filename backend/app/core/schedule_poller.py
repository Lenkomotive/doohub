import asyncio
import logging
from datetime import datetime, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from croniter import croniter

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.slave_client import slave
from app.models.pipeline import Pipeline
from app.models.pipeline_schedule import PipelineSchedule
from app.models.pipeline_template import PipelineTemplate

logger = logging.getLogger(__name__)

POLL_INTERVAL = 30  # seconds


async def schedule_poller():
    """Background task polling for due schedules. Runs forever."""
    logger.info("Schedule poller started (interval=%ds)", POLL_INTERVAL)
    while True:
        try:
            await _poll_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.exception("Schedule poller error")
        await asyncio.sleep(POLL_INTERVAL)


async def _poll_once():
    """Single poll: find and execute all due schedules."""
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due = (
            db.query(PipelineSchedule)
            .filter(
                PipelineSchedule.is_active == True,  # noqa: E712
                PipelineSchedule.next_run_at <= now,
            )
            .all()
        )
        for schedule in due:
            try:
                await _execute_schedule(db, schedule, now)
            except Exception:
                logger.exception("Failed to execute schedule %d", schedule.id)
    finally:
        db.close()


async def _execute_schedule(db, schedule: PipelineSchedule, now: datetime):
    """Create and fire a pipeline from a schedule."""
    # Concurrency guard
    if schedule.skip_if_running:
        running = (
            db.query(Pipeline)
            .filter(
                Pipeline.schedule_id == schedule.id,
                Pipeline.status.in_(["planning", "developing", "reviewing"]),
            )
            .first()
        )
        if running:
            # Advance next_run_at so we don't re-trigger every poll
            if schedule.schedule_type == "recurring":
                schedule.next_run_at = compute_next_run(
                    schedule.cron_expression, schedule.timezone
                )
            else:
                schedule.is_active = False
                schedule.next_run_at = None
            db.commit()
            logger.info("Skipping schedule %d — previous run still active", schedule.id)
            return

    # Resolve template
    template_definition = None
    if schedule.template_id:
        template = (
            db.query(PipelineTemplate)
            .filter(PipelineTemplate.id == schedule.template_id)
            .first()
        )
        if template:
            template_definition = template.definition

    # Create pipeline
    pipeline_key = uuid4().hex[:12]
    pipeline = Pipeline(
        user_id=schedule.user_id,
        pipeline_key=pipeline_key,
        repo_path=schedule.repo_path,
        issue_number=schedule.issue_number,
        task_description=schedule.task_description,
        model=schedule.model,
        template_id=schedule.template_id,
        schedule_id=schedule.id,
    )
    db.add(pipeline)

    # Update schedule metadata
    schedule.last_run_at = now
    if schedule.schedule_type == "once":
        schedule.is_active = False
        schedule.next_run_at = None
    else:
        schedule.next_run_at = compute_next_run(
            schedule.cron_expression, schedule.timezone
        )

    db.commit()

    # Fire to slave
    callback_url = f"{settings.backend_internal_url}/internal/pipelines/callback"
    try:
        await slave.start_pipeline(
            pipeline_key=pipeline_key,
            repo_path=schedule.repo_path,
            issue_number=schedule.issue_number,
            task_description=schedule.task_description,
            model=schedule.model,
            callback_url=callback_url,
            template_definition=template_definition,
        )
        logger.info("Schedule %d fired → pipeline %s", schedule.id, pipeline_key)
    except Exception:
        pipeline.status = "failed"
        pipeline.error = "Failed to reach slave service"
        db.commit()
        logger.exception("Schedule %d: failed to start pipeline %s", schedule.id, pipeline_key)


def compute_next_run(cron_expression: str, tz_name: str) -> datetime:
    """Compute next run time from cron expression, returned as UTC."""
    tz = ZoneInfo(tz_name)
    cron = croniter(cron_expression, datetime.now(tz))
    return cron.get_next(datetime).astimezone(timezone.utc)
