from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app import orchestrator
from app.auth import require_api_key
from app.config import settings

router = APIRouter(prefix="/api/orchestrate", dependencies=[Depends(require_api_key)])


class StartPipelineRequest(BaseModel):
    pipeline_key: str
    repo_path: str
    issue_number: int | None = None
    task_description: str | None = None
    model: str = "claude-sonnet-4-6"
    callback_url: str


@router.post("")
async def start_pipeline(body: StartPipelineRequest):
    try:
        orchestrator.start(
            pipeline_key=body.pipeline_key,
            repo_path=body.repo_path,
            issue_number=body.issue_number,
            task_description=body.task_description,
            model=body.model,
            callback_url=body.callback_url,
            api_key=settings.api_key,
        )
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))
    return {"status": "started", "pipeline_key": body.pipeline_key}


@router.post("/{pipeline_key}/cancel")
async def cancel_pipeline(pipeline_key: str):
    if orchestrator.cancel(pipeline_key):
        return {"status": "cancelled"}
    raise HTTPException(status_code=404, detail="Pipeline not running")


class CleanupRequest(BaseModel):
    repo_path: str
    branch: str | None = None
    pr_number: int | None = None


@router.post("/{pipeline_key}/cleanup")
async def cleanup_pipeline(pipeline_key: str, body: CleanupRequest):
    await orchestrator.cleanup(
        pipeline_key=pipeline_key,
        repo_path=body.repo_path,
        branch=body.branch,
        pr_number=body.pr_number,
    )
    return {"status": "cleaned"}


@router.get("/status")
async def list_running():
    return {"running": orchestrator.running_keys()}
