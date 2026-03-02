import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app import claude_runner
from app.auth import require_api_key
from app.event_bus import event_bus
from app.runner import busy_keys, get_queue, start_run

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", dependencies=[Depends(require_api_key)])


class RunRequest(BaseModel):
    session_key: str
    message: str
    project_path: str = "/projects"
    model: str = "claude-opus-4-6"
    claude_session_id: str | None = None
    interactive: bool = False
    timeout: int = 300


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("/events")
async def events():
    """SSE stream of status events. Sends initial snapshot of currently busy sessions."""
    q = event_bus.subscribe()

    async def generate():
        yield _sse("snapshot", {"sessions": {k: "busy" for k in busy_keys()}})
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=25)
                    yield _sse(event["event"], event)
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            event_bus.unsubscribe(q)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/run")
async def run(req: RunRequest):
    """Blocking Claude run. Used by the backend for the standard send-message flow."""
    if req.session_key in busy_keys():
        raise HTTPException(status_code=409, detail="Session is busy")

    from app.runner import _set_status
    await _set_status(req.session_key, "busy")
    try:
        result = await claude_runner.run_prompt(
            prompt=req.message,
            project_path=req.project_path,
            model=req.model,
            claude_session_id=req.claude_session_id,
            timeout=req.timeout,
            session_key=req.session_key,
            interactive=req.interactive,
        )
    finally:
        await _set_status(req.session_key, "idle")

    return result


@router.post("/run/stream")
async def run_stream(req: RunRequest):
    """SSE streaming run. Claude runs as a background task — safe to disconnect."""
    if req.session_key in busy_keys():
        q = get_queue(req.session_key)
        if q is None:
            raise HTTPException(status_code=409, detail="Session is busy")
    else:
        q = await start_run(
            req.session_key, req.message, req.project_path,
            req.model, req.claude_session_id, req.interactive, req.timeout,
        )

    async def generate():
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=25)
                    yield _sse(event["event"], event)
                    if event.get("event") in ("done", "error"):
                        break
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        except asyncio.CancelledError:
            pass  # Client disconnected — Claude keeps running

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/cancel/{key}")
async def cancel(key: str):
    cancelled = await claude_runner.cancel(key)
    if cancelled:
        from app.runner import _set_status
        await _set_status(key, "idle")
    return {"session_key": key, "cancelled": cancelled}
