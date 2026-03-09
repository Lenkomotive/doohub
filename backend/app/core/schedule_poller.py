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


def compute_next_run(cron_expression: str, tz_name: str) -> datetime:
    tz = ZoneInfo(tz_name)
    now = datetime.now(tz)
    cron = croniter(cron_expression, now)
    return cron.get_next(datetime).astimezone(timezone.utc)


def _resolve_nested_templates(db, definition: dict, max_depth: int = 5, _visited=None, _depth=0):
    """Same logic as pipelines.py but usable outside request context."""
    if _depth >= max_depth:
        return {}
    if _visited is None:
        _visited = set()
    result = {}
    for node in definition.get("nodes", []):
        if node.get("type") != "template":
            continue
        tid = node.get("template_id")
        if not tid or int(tid) in _visited or str(tid) in result:
            continue
        tpl = db.query(PipelineTemplate).filter(PipelineTemplate.id == int(tid)).first()
        if not tpl:
            continue
        result[str(tid)] = tpl.definition
        _visited.add(int(tid))
        result.update(_resolve_nested_templates(db, tpl.definition, max_depth, _visited, _depth + 1))
        _visited.discard(int(tid))
    return result


async def _execute_schedule(db, schedule: PipelineSchedule) -> None:
    """Create and fire a pipeline for the given schedule."""
    pipeline_key = uuid4().hex[:12]

    # Resolve template
    template_definition = None
    nested_templates = None
    if schedule.template_id:
        template = db.query(PipelineTemplate).filter(
            PipelineTemplate.id == schedule.template_id
        ).first()
        if template:
            template_definition = template.definition
            nested_templates = _resolve_nested_templates(db, template_definition)
        else:
            logger.warning("Schedule %d references missing template %d", schedule.id, schedule.template_id)
            return

    if not template_definition:
        logger.warning("Schedule %d has no template, skipping", schedule.id)
        return

    pipeline = Pipeline(
        user_id=schedule.user_id,
        pipeline_key=pipeline_key,
        repo_path=schedule.repo_path,
        issue_number=schedule.issue_number,
        issue_title=schedule.task_description,
        task_description=schedule.task_description,
        model=schedule.model,
        template_id=schedule.template_id,
        schedule_id=schedule.id,
    )
    db.add(pipeline)
    db.flush()

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
            nested_templates=nested_templates,
        )
        logger.info("Schedule %d fired pipeline %s", schedule.id, pipeline_key)
    except Exception:
        pipeline.status = "failed"
        pipeline.error = "Failed to reach slave service"
        logger.exception("Schedule %d failed to start pipeline", schedule.id)

    # Update schedule bookkeeping
    schedule.last_run_at = datetime.now(timezone.utc)
    schedule.run_count += 1

    if schedule.schedule_type == "once":
        schedule.is_active = False
        schedule.next_run_at = None
    else:
        schedule.next_run_at = compute_next_run(schedule.cron_expression, schedule.timezone)

    db.commit()


async def _poll_once() -> None:
    db = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        due = (
            db.query(PipelineSchedule)
            .filter(
                PipelineSchedule.is_active.is_(True),
                PipelineSchedule.next_run_at <= now,
            )
            .with_for_update(skip_locked=True)
            .limit(10)
            .all()
        )

        for schedule in due:
            # skip_if_running: check if there's already a running pipeline for this schedule
            if schedule.skip_if_running:
                running = db.query(Pipeline).filter(
                    Pipeline.schedule_id == schedule.id,
                    Pipeline.status.in_(["planning", "developing", "reviewing"]),
                ).first()
                if running:
                    logger.debug("Schedule %d skipped — pipeline %s still running", schedule.id, running.pipeline_key)
                    continue

            await _execute_schedule(db, schedule)
    except Exception:
        logger.exception("Schedule poller error")
    finally:
        db.close()


async def run_schedule_poller() -> None:
    """Background task: poll for due schedules every POLL_INTERVAL seconds."""
    logger.info("Schedule poller started (interval=%ds)", POLL_INTERVAL)
    while True:
        await _poll_once()
        await asyncio.sleep(POLL_INTERVAL)
