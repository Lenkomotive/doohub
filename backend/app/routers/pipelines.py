import asyncio
import json
import logging
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from app.core.auth import get_current_user, require_slave_api_key
from app.core.config import settings
from app.core.database import get_db
from app.core.fcm import send_push
from app.core.pipeline_events import pipeline_events
from app.core.slave_client import slave
from app.models.pipeline import Pipeline
from app.models.pipeline_template import PipelineTemplate
from app.models.user import User

from app.schemas.pipeline import CreatePipelineRequest, PipelineCallbackRequest

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pipelines"])


@router.post("/pipelines", status_code=201)
async def create_pipeline(
    body: CreatePipelineRequest,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pipeline_key = uuid4().hex[:12]

    # Look up template definition (required)
    if not body.template_id:
        raise HTTPException(status_code=400, detail="template_id is required")
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
                    yield f"event: pipeline\ndata: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            pipeline_events.unsubscribe(q)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/pipelines/{pipeline_key}")
async def get_pipeline(
    pipeline_key: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    pipeline = _get_user_pipeline(db, pipeline_key, user.id)
    return _serialize(pipeline)


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

    event = {"pipeline_key": body.pipeline_key, "status": body.status}
    if body.step_log:
        event["step_log"] = body.step_log
    if body.step:
        event["step"] = body.step.model_dump()
    if body.pr_url:
        event["pr_url"] = body.pr_url
    if body.error:
        event["error"] = body.error
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
        "template_id": p.template_id,
        "template_name": p.template.name if p.template else None,
        "step_logs": p.step_logs or [],
        "created_at": p.created_at.isoformat(),
        "updated_at": p.updated_at.isoformat(),
    }
