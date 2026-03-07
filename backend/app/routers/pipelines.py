import asyncio
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from app.core.auth import get_current_user, require_slave_api_key
from app.core.config import settings
from app.core.database import get_db
from app.core.fcm import send_push
from app.core.pipeline_events import classify_event, pipeline_events
from app.core.slave_client import slave
from app.models.pipeline import Pipeline
from app.models.pipeline_template import PipelineTemplate
from app.models.user import User

from app.schemas.pipeline import (
    CreatePipelineRequest,
    DashboardPipeline,
    DashboardResponse,
    DashboardSummary,
    PipelineCallbackRequest,
    StepsResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pipelines"])


ACTIVE_STATUSES = {"planning", "developing", "reviewing", "running"}
TERMINAL_STATUSES = {"done", "failed", "cancelled", "merged"}


@router.post("/pipelines", status_code=201)
async def create_pipeline(
    body: CreatePipelineRequest,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pipeline_key = uuid4().hex[:12]

    # Look up template definition if template_id is provided
    template_definition = None
    if body.template_id:
        template = db.query(PipelineTemplate).filter(PipelineTemplate.id == body.template_id).first()
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        template_definition = template.definition

    pipeline = Pipeline(
        user_id=user.id,
        pipeline_key=pipeline_key,
        repo_path=body.repo_path,
        issue_number=body.issue_number,
        issue_title=body.task_description,
        task_description=body.task_description,
        model=body.model,
        template_id=body.template_id,
    )
    db.add(pipeline)
    db.commit()

    callback_url = f"{settings.backend_internal_url}/internal/pipelines/callback"

    # Fire-and-forget to slave
    try:
        await slave.start_pipeline(
            pipeline_key=pipeline_key,
            repo_path=body.repo_path,
            issue_number=body.issue_number,
            task_description=body.task_description,
            model=body.model,
            callback_url=callback_url,
            template_definition=template_definition,
        )
    except HTTPException:
        pipeline.status = "failed"
        pipeline.error = "Failed to reach slave service"
        db.commit()
        raise

    return {
        "pipeline_key": pipeline_key,
        "status": pipeline.status,
    }


@router.get("/pipelines")
async def list_pipelines(
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pipelines = (
        db.query(Pipeline)
        .filter(Pipeline.user_id == user.id)
        .order_by(Pipeline.created_at.desc())
        .all()
    )
    return {
        "pipelines": [_serialize(p) for p in pipelines],
        "total": len(pipelines),
    }


@router.get("/pipelines/events")
async def pipeline_sse(
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    user_id = user.id
    user_keys = {
        p.pipeline_key
        for p in db.query(Pipeline).filter(Pipeline.user_id == user_id).all()
    }

    async def generate():
        # Send catch-up events from the ring buffer
        recent = pipeline_events.get_recent()
        for evt in recent:
            pk = evt.get("pipeline_key")
            if pk in user_keys:
                event_type = evt.get("event_type", "pipeline")
                yield f"event: {event_type}\ndata: {json.dumps(evt)}\n\n"

        q = pipeline_events.subscribe()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                pk = event.get("pipeline_key")
                if pk not in user_keys:
                    # Check if this is a newly created pipeline for this user
                    p = db.query(Pipeline).filter(
                        Pipeline.pipeline_key == pk, Pipeline.user_id == user_id
                    ).first()
                    if p:
                        user_keys.add(pk)
                if pk in user_keys:
                    event_type = event.get("event_type", "pipeline")
                    yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            pipeline_events.unsubscribe(q)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/pipelines/dashboard", response_model=DashboardResponse)
async def pipeline_dashboard(
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pipelines = (
        db.query(Pipeline)
        .filter(Pipeline.user_id == user.id)
        .order_by(Pipeline.created_at.desc())
        .all()
    )

    running = 0
    completed = 0
    failed = 0
    items: list[DashboardPipeline] = []

    now = datetime.now(timezone.utc)

    for p in pipelines:
        if p.status in ACTIVE_STATUSES:
            running += 1
        elif p.status in ("done", "merged"):
            completed += 1
        elif p.status == "failed":
            failed += 1

        # Derive current_node from step_logs
        current_node = None
        step_logs = p.step_logs or []
        if step_logs:
            running_steps = [s for s in step_logs if s.get("status") == "running"]
            if running_steps:
                current_node = running_steps[-1].get("node_name")
            else:
                current_node = step_logs[-1].get("node_name")

        # Compute duration
        created = p.created_at
        updated = p.updated_at
        if p.status in TERMINAL_STATUSES and updated and created:
            duration_s = round((updated - created).total_seconds(), 1)
        elif created:
            duration_s = round((now - created).total_seconds(), 1)
        else:
            duration_s = None

        items.append(DashboardPipeline(
            pipeline_key=p.pipeline_key,
            issue_number=p.issue_number,
            issue_title=p.issue_title,
            repo_path=p.repo_path,
            status=p.status,
            current_node=current_node,
            model=p.model,
            total_cost_usd=p.total_cost_usd,
            duration_s=duration_s,
            started_at=created.isoformat() if created else "",
            updated_at=updated.isoformat() if updated else "",
        ))

    return DashboardResponse(
        summary=DashboardSummary(
            running=running,
            completed=completed,
            failed=failed,
            total=len(pipelines),
        ),
        pipelines=items,
    )


@router.get("/pipelines/{pipeline_key}")
async def get_pipeline(
    pipeline_key: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pipeline = _get_user_pipeline(db, pipeline_key, user.id)
    return _serialize(pipeline)


@router.get("/pipelines/{pipeline_key}/steps", response_model=StepsResponse)
async def get_pipeline_steps(
    pipeline_key: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pipeline = _get_user_pipeline(db, pipeline_key, user.id)
    return StepsResponse(
        pipeline_key=pipeline.pipeline_key,
        status=pipeline.status,
        steps=pipeline.step_logs or [],
    )


@router.get("/pipelines/{pipeline_key}/stream")
async def pipeline_key_sse(
    pipeline_key: str,
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    pipeline = _get_user_pipeline(db, pipeline_key, user.id)

    async def generate():
        # Send catch-up events from the ring buffer
        recent = pipeline_events.get_recent(pipeline_key=pipeline.pipeline_key)
        for evt in recent:
            event_type = evt.get("event_type", "pipeline")
            yield f"event: {event_type}\ndata: {json.dumps(evt)}\n\n"

        q = pipeline_events.subscribe()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                if event.get("pipeline_key") == pipeline.pipeline_key:
                    event_type = event.get("event_type", "pipeline")
                    yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            pipeline_events.unsubscribe(q)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/pipelines/{pipeline_key}/cancel")
async def cancel_pipeline(
    pipeline_key: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pipeline = _get_user_pipeline(db, pipeline_key, user.id)
    try:
        await slave.cancel_pipeline(pipeline_key)
    except HTTPException:
        pass
    pipeline.status = "cancelled"
    db.commit()
    await pipeline_events.publish({"pipeline_key": pipeline_key, "status": "cancelled"})
    return {"status": "cancelled"}


@router.delete("/pipelines/{pipeline_key}", status_code=204)
async def delete_pipeline(
    pipeline_key: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pipeline = _get_user_pipeline(db, pipeline_key, user.id)

    # Clean up worktree, PR, and branch on the slave
    try:
        await slave.cleanup_pipeline(
            pipeline_key=pipeline_key,
            repo_path=pipeline.repo_path,
            branch=pipeline.branch,
            pr_number=pipeline.pr_number,
        )
    except HTTPException:
        logger.warning("Cleanup failed for pipeline %s, deleting anyway", pipeline_key)

    db.delete(pipeline)
    db.commit()


@router.get("/pipelines/{pipeline_key}/merge-status")
async def get_merge_status(
    pipeline_key: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pipeline = _get_user_pipeline(db, pipeline_key, user.id)
    if pipeline.status not in ("done", "merged"):
        raise HTTPException(status_code=400, detail="Pipeline is not done yet")
    if not pipeline.pr_number:
        raise HTTPException(status_code=400, detail="Pipeline has no PR")
    return await slave.check_merge_status(pipeline.repo_path, pipeline.pr_number)


@router.post("/pipelines/{pipeline_key}/merge")
async def merge_pipeline(
    pipeline_key: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pipeline = _get_user_pipeline(db, pipeline_key, user.id)
    if pipeline.status != "done":
        raise HTTPException(status_code=400, detail="Pipeline is not in done status")
    if not pipeline.pr_number:
        raise HTTPException(status_code=400, detail="Pipeline has no PR")

    result = await slave.merge_pipeline(pipeline_key, pipeline.repo_path, pipeline.pr_number)
    if result.get("success"):
        pipeline.status = "merged"
        db.commit()
        await pipeline_events.publish({"pipeline_key": pipeline_key, "status": "merged"})
    return result


# --- internal callback (slave -> backend) ---


@router.post("/internal/pipelines/callback")
async def pipeline_callback(
    body: PipelineCallbackRequest,
    db: DBSession = Depends(get_db),
    _auth: None = Depends(require_slave_api_key),
):
    pipeline = db.query(Pipeline).filter(
        Pipeline.pipeline_key == body.pipeline_key
    ).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    previous_status = pipeline.status

    pipeline.status = body.status
    if body.issue_title is not None:
        pipeline.issue_title = body.issue_title
    if body.plan is not None:
        pipeline.plan = body.plan
    if body.branch is not None:
        pipeline.branch = body.branch
    if body.pr_number is not None:
        pipeline.pr_number = body.pr_number
    if body.pr_url is not None:
        pipeline.pr_url = body.pr_url
    if body.error is not None:
        pipeline.error = body.error
    if body.cost_usd is not None:
        pipeline.total_cost_usd += body.cost_usd
    if body.claude_session_id is not None:
        pipeline.claude_session_id = body.claude_session_id

    # Accumulate step logs
    if body.step:
        logs = list(pipeline.step_logs or [])
        step_dict = body.step.model_dump()
        # Update existing step or append new one
        existing_idx = next((i for i, s in enumerate(logs) if s["node_id"] == step_dict["node_id"]), None)
        if existing_idx is not None and step_dict["status"] in ("completed", "failed"):
            logs[existing_idx] = step_dict
        elif existing_idx is None:
            logs.append(step_dict)
        pipeline.step_logs = logs

    db.commit()

    # Build enriched event
    event: dict = {
        "pipeline_key": body.pipeline_key,
        "status": body.status,
        "user_id": pipeline.user_id,
        "previous_status": previous_status,
    }
    if body.step:
        event["step"] = body.step.model_dump()
        event["node_id"] = body.step.node_id
        event["node_name"] = body.step.node_name
    if body.step_log:
        event["step_log"] = body.step_log
    if body.pr_url:
        event["pr_url"] = body.pr_url
    if body.error:
        event["error"] = body.error
    if body.cost_usd is not None:
        event["cost_usd"] = body.cost_usd

    event["event_type"] = classify_event(event)
    await pipeline_events.publish(event)

    if body.status in ("done", "failed"):
        user = db.query(User).filter(User.id == pipeline.user_id).first()
        if user and user.fcm_token and user.notify_pipelines:
            title = "Pipeline finished" if body.status == "done" else "Pipeline failed"
            desc = pipeline.issue_title or pipeline.task_description or ""
            send_push(user.fcm_token, title, desc, {"pipeline_key": body.pipeline_key})

    return {"ok": True}


# --- helpers ---


def _get_user_pipeline(db: DBSession, pipeline_key: str, user_id: int) -> Pipeline:
    pipeline = db.query(Pipeline).filter(
        Pipeline.pipeline_key == pipeline_key, Pipeline.user_id == user_id
    ).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline


def _serialize(p: Pipeline) -> dict:
    return {
        "pipeline_key": p.pipeline_key,
        "repo_path": p.repo_path,
        "issue_number": p.issue_number,
        "issue_title": p.issue_title,
        "task_description": p.task_description,
        "status": p.status,
        "plan": p.plan,
        "branch": p.branch,
        "pr_number": p.pr_number,
        "pr_url": p.pr_url,
        "error": p.error,
        "review_round": p.review_round,
        "model": p.model,
        "total_cost_usd": p.total_cost_usd,
        "step_logs": p.step_logs or [],
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }
