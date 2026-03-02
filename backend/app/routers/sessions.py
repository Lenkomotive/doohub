from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.provider_client import provider
from app.models.session import Pipeline, SessionMessage
from app.models.user import User
from app.schemas.session import (
    CreateSessionRequest,
    PipelineListResponse,
    PipelineResponse,
    SendMessageRequest,
)

router = APIRouter(tags=["sessions"])


# --- repos ---


@router.get("/repos")
async def list_repos(_user: User = Depends(get_current_user)):
    """List available repos from the provider."""
    return await provider.list_repos()


# --- sessions ---


@router.post("/sessions", status_code=201)
async def create_session(
    body: CreateSessionRequest,
    _user: User = Depends(get_current_user),
):
    """Create a new session on the provider."""
    return await provider.create_session(
        key=body.session_key,
        model=body.model,
        path=body.project_path,
        interactive=body.interactive,
    )


@router.get("/sessions")
async def list_sessions(
    status: str | None = Query(None),
    _user: User = Depends(get_current_user),
):
    """List all sessions from the provider."""
    data = await provider.list_sessions()
    # Provider returns {"sessions": {"key": {...}, ...}} — transform to array
    raw = data.get("sessions", {})
    sessions = []
    for key, info in raw.items():
        entry = {"session_key": key, **info}
        if status and entry.get("status") != status:
            continue
        sessions.append(entry)
    return {"sessions": sessions, "total": len(sessions)}


@router.get("/sessions/{session_key}")
async def get_session(
    session_key: str,
    _user: User = Depends(get_current_user),
):
    """Get a session by key from the provider."""
    return await provider.get_session(session_key)


@router.delete("/sessions/{session_key}", status_code=204)
async def delete_session(
    session_key: str,
    _user: User = Depends(get_current_user),
):
    """Delete a session on the provider."""
    await provider.delete_session(session_key)


@router.post("/sessions/{session_key}/messages")
async def send_message(
    session_key: str,
    body: SendMessageRequest,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Send a message to a session via the provider.

    Also saves a copy of both the user message and the assistant response
    in DooHub's local DB for history / caching.
    """
    # Save user message locally
    user_msg = SessionMessage(
        session_key=session_key, role="user", content=body.content
    )
    db.add(user_msg)
    db.commit()

    # Proxy to provider
    result = await provider.send_message(session_key, body.content)

    # Save assistant response locally
    response_text = result.get("result") or result.get("error") or ""
    assistant_msg = SessionMessage(
        session_key=session_key, role="assistant", content=response_text
    )
    db.add(assistant_msg)
    db.commit()

    return {
        "role": "assistant",
        "content": response_text,
        "session_id": result.get("session_id"),
        "cost_usd": result.get("cost_usd"),
    }


@router.post("/sessions/{session_key}/cancel")
async def cancel_session(
    session_key: str,
    _user: User = Depends(get_current_user),
):
    """Cancel a running session on the provider."""
    return await provider.cancel_session(session_key)


# --- message history (local) ---


@router.get("/sessions/{session_key}/history")
def get_message_history(
    session_key: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    """Get locally cached message history for a session."""
    query = db.query(SessionMessage).filter(
        SessionMessage.session_key == session_key
    )
    total = query.count()
    messages = (
        query.order_by(SessionMessage.created_at)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
        "total": total,
    }


# --- pipelines ---


@router.get("/pipelines", response_model=PipelineListResponse)
def list_pipelines(
    status: str | None = Query(None),
    limit: int = Query(20, le=100),
    offset: int = Query(0),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    query = db.query(Pipeline)
    if status:
        query = query.filter(Pipeline.status == status)

    total = query.count()
    pipelines = (
        query.order_by(desc(Pipeline.started_at))
        .offset(offset)
        .limit(limit)
        .all()
    )
    return PipelineListResponse(pipelines=pipelines, total=total)


@router.get("/pipelines/{pipeline_id}", response_model=PipelineResponse)
def get_pipeline(
    pipeline_id: int,
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    pipeline = db.query(Pipeline).filter(Pipeline.id == pipeline_id).first()
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return pipeline
