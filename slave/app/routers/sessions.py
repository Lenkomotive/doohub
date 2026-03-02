import asyncio
import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.auth import require_api_key
from app.event_bus import event_bus
from app.run_manager import get_queue, start_run
from app.session_store import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/sessions", dependencies=[Depends(require_api_key)])


class CreateSessionRequest(BaseModel):
    session_key: str
    model: str = "claude-opus-4-6"
    project_path: str = "/projects"
    interactive: bool = False


class SendMessageRequest(BaseModel):
    message: str
    timeout: int = 300


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.get("")
async def list_sessions():
    return {"sessions": store.list_all()}


@router.post("", status_code=201)
async def create_session(req: CreateSessionRequest):
    if store.get(req.session_key):
        raise HTTPException(status_code=409, detail="Session already exists")
    store.add(req.session_key, req.project_path, req.model)
    if req.interactive:
        store.set_interactive(req.session_key, True)
    return {"session_key": req.session_key, "status": "created"}


@router.get("/events")
async def session_events():
    """SSE stream of all status events plus an initial snapshot."""
    q = event_bus.subscribe()

    async def generate():
        yield _sse("snapshot", {"sessions": store.list_all()})
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


@router.get("/{key}")
async def get_session(key: str):
    session = store.get(key)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"session_key": key, **session}


@router.delete("/{key}")
async def delete_session(key: str):
    if not store.get(key):
        raise HTTPException(status_code=404, detail="Session not found")
    from app import claude_runner
    cancelled = await claude_runner.cancel(key)
    store.remove(key)
    return {"session_key": key, "cancelled": cancelled, "status": "deleted"}


@router.post("/{key}/message")
async def send_message(key: str, req: SendMessageRequest):
    """Blocking send — kept for backwards-compatibility (Telegram bot uses this)."""
    session = store.get(key)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("status") == "busy":
        raise HTTPException(status_code=409, detail="Session is busy")

    store.set_status(key, "busy")
    from app import claude_runner
    try:
        result = await claude_runner.run_prompt(
            prompt=req.message,
            project_path=session["project_path"],
            model=session.get("model", "claude-opus-4-6"),
            claude_session_id=session.get("claude_session_id"),
            timeout=req.timeout,
            session_key=key,
            interactive=session.get("interactive", False),
        )
    except Exception as e:
        store.set_status(key, "idle")
        raise HTTPException(status_code=500, detail=str(e))

    new_sid = result.get("session_id")
    if new_sid:
        store.set_claude_session_id(key, new_sid)
    store.set_status(key, "idle")

    return {
        "type": result.get("type", "unknown"),
        "result": result.get("result"),
        "error": result.get("error"),
        "session_id": new_sid,
        "cost_usd": result.get("cost_usd"),
    }


@router.post("/{key}/message/stream")
async def send_message_stream(key: str, req: SendMessageRequest):
    """Stream tokens via SSE. Claude runs as a background task —
    client disconnect is safe and does NOT cancel Claude."""
    session = store.get(key)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.get("status") == "busy":
        # If there's already a run queue, let the client re-attach to it
        q = get_queue(key)
        if q is None:
            raise HTTPException(status_code=409, detail="Session is busy")
    else:
        store.set_status(key, "busy")
        q = await start_run(key, session, store, event_bus, req.message, req.timeout)

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
            pass  # Client disconnected — Claude keeps running in background

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/{key}/cancel")
async def cancel_session(key: str):
    session = store.get(key)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    from app import claude_runner
    cancelled = await claude_runner.cancel(key)
    if session.get("status") == "busy":
        store.set_status(key, "idle")
    return {"session_key": key, "cancelled": cancelled}
