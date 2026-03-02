import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.provider_client import provider
from app.models.session import Session, SessionMessage
from app.models.user import User
from app.schemas.session import CreateSessionRequest, SendMessageRequest

router = APIRouter(tags=["sessions"])


# --- repos ---


@router.get("/repos")
async def list_repos(_user: User = Depends(get_current_user)):
    return await provider.list_repos()


# --- sessions ---


@router.post("/sessions", status_code=201)
async def create_session(
    body: CreateSessionRequest,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await provider.create_session(
        key=body.session_key,
        model=body.model,
        path=body.project_path,
        interactive=body.interactive,
    )
    session = Session(user_id=user.id, session_key=body.session_key)
    db.add(session)
    db.commit()
    return {"session_key": body.session_key}


@router.get("/sessions/events")
async def session_events(
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """SSE stream of status events filtered to this user's sessions."""
    user_keys = {
        s.session_key
        for s in db.query(Session).filter(Session.user_id == user.id).all()
    }

    async def generate():
        async for event in provider.stream_events():
            evt = event.get("event")
            if evt == "snapshot":
                # Filter snapshot to only this user's sessions
                all_sessions = event.get("sessions", {})
                filtered = {k: v for k, v in all_sessions.items() if k in user_keys}
                yield f"event: snapshot\ndata: {json.dumps({'sessions': filtered})}\n\n"
            elif evt == "status" and event.get("session_key") in user_keys:
                yield f"event: status\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/sessions")
async def list_sessions(
    status: str | None = Query(None),
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    data = await provider.list_sessions()
    provider_sessions = data.get("sessions", {})

    local = db.query(Session).filter(Session.user_id == user.id).all()
    sessions = []
    for s in local:
        info = provider_sessions.get(s.session_key, {})
        entry = {
            "session_key": s.session_key,
            "created_at": s.created_at.isoformat(),
            "status": "idle",
            "model": "",
            "project_path": "",
            "interactive": False,
            "claude_session_id": None,
            **info,
        }
        if status and entry.get("status") != status:
            continue
        sessions.append(entry)
    return {"sessions": sessions, "total": len(sessions)}


@router.get("/sessions/{session_key}")
async def get_session(
    session_key: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.query(Session).filter(
        Session.session_key == session_key, Session.user_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return await provider.get_session(session_key)


@router.delete("/sessions/{session_key}", status_code=204)
async def delete_session(
    session_key: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.query(Session).filter(
        Session.session_key == session_key, Session.user_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    await provider.delete_session(session_key)
    db.delete(session)
    db.commit()


@router.post("/sessions/{session_key}/messages")
async def send_message(
    session_key: str,
    body: SendMessageRequest,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.query(Session).filter(
        Session.session_key == session_key, Session.user_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.add(SessionMessage(session_id=session.id, role="user", content=body.content))
    db.commit()

    result = await provider.send_message(session_key, body.content)

    response_text = result.get("result") or result.get("error") or ""
    db.add(SessionMessage(session_id=session.id, role="assistant", content=response_text))
    db.commit()

    return {
        "role": "assistant",
        "content": response_text,
        "session_id": result.get("session_id"),
        "cost_usd": result.get("cost_usd"),
    }


@router.post("/sessions/{session_key}/messages/stream")
async def send_message_stream(
    session_key: str,
    body: SendMessageRequest,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """SSE endpoint — streams tokens as Claude responds, saves to DB on done."""
    session = db.query(Session).filter(
        Session.session_key == session_key, Session.user_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.add(SessionMessage(session_id=session.id, role="user", content=body.content))
    db.commit()
    session_id = session.id  # capture before leaving thread

    async def generate():
        result_text = ""
        async for event in provider.stream_message(session_key, body.content):
            evt = event.get("event")
            if evt == "token":
                result_text += event.get("token", "")
            elif evt == "done":
                result_text = event.get("result", result_text)
                # Persist assistant message
                from app.core.database import SessionLocal
                with SessionLocal() as save_db:
                    save_db.add(SessionMessage(
                        session_id=session_id,
                        role="assistant",
                        content=result_text,
                    ))
                    save_db.commit()
            yield f"event: {evt}\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.post("/sessions/{session_key}/cancel")
async def cancel_session(
    session_key: str,
    _user: User = Depends(get_current_user),
):
    return await provider.cancel_session(session_key)


@router.get("/sessions/{session_key}/history")
def get_message_history(
    session_key: str,
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.query(Session).filter(
        Session.session_key == session_key, Session.user_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    total = len(session.messages)
    messages = (
        db.query(SessionMessage)
        .filter(SessionMessage.session_id == session.id)
        .order_by(SessionMessage.created_at)
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {
        "messages": [
            {"id": m.id, "role": m.role, "content": m.content, "created_at": m.created_at.isoformat()}
            for m in messages
        ],
        "total": total,
    }
