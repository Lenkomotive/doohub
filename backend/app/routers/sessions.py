import asyncio
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session as DBSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.core.fcm import send_push
from app.core.session_events import session_events as session_event_bus
from app.core.slave_client import slave
from app.models.session import Session, SessionMessage
from app.models.user import User
from app.schemas.session import CreateSessionRequest

router = APIRouter(tags=["sessions"])


# --- repos ---


@router.get("/repos")
async def list_repos(_user: User = Depends(get_current_user)):
    return await slave.list_repos()


@router.get("/repos/issues")
async def list_repo_issues(
    repo_path: str = Query(...),
    per_page: int = Query(30, ge=1, le=100),
    cursor: str | None = Query(None),
    _user: User = Depends(get_current_user),
):
    return await slave.list_issues(repo_path, per_page=per_page, cursor=cursor)


@router.get("/repos/issue")
async def get_repo_issue(
    repo_path: str = Query(...),
    issue_number: int = Query(...),
    _user: User = Depends(get_current_user),
):
    return await slave.fetch_issue(repo_path, issue_number)


# --- sessions ---


@router.post("/sessions", status_code=201)
async def create_session(
    body: CreateSessionRequest,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session_key = uuid4().hex[:12]
    name = body.name or await slave.generate_name()
    session = Session(
        user_id=user.id,
        session_key=session_key,
        name=name,
        project_path=body.project_path,
        model=body.model,
    )
    db.add(session)
    db.commit()
    return {"session_key": session_key, "name": name}


@router.get("/sessions/events")
async def session_events(
    user: User = Depends(get_current_user),
    db: DBSession = Depends(get_db),
):
    """SSE stream of status events, filtered to this user's sessions."""
    user_sessions = db.query(Session).filter(Session.user_id == user.id).all()
    user_keys = {s.session_key for s in user_sessions}
    session_map = {
        s.session_key: {
            "name": s.name,
            "model": s.model,
            "project_path": s.project_path,
            "interactive": s.interactive,
            "claude_session_id": s.claude_session_id,
        }
        for s in user_sessions
    }

    async def generate():
        snapshot_sent = False
        q = session_event_bus.subscribe()
        try:
            while True:
                try:
                    event = await asyncio.wait_for(q.get(), timeout=30)
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                evt = event.get("event")
                if evt == "snapshot" and not snapshot_sent:
                    busy_keys = set(event.get("sessions", {}).keys())
                    merged = {
                        key: {
                            **session_map[key],
                            "status": "busy" if key in busy_keys else "idle",
                        }
                        for key in user_keys
                    }
                    yield f"event: snapshot\ndata: {json.dumps({'sessions': merged})}\n\n"
                    snapshot_sent = True
                elif evt == "status" and event.get("session_key") in user_keys:
                    yield f"event: status\ndata: {json.dumps(event)}\n\n"
        except asyncio.CancelledError:
            pass
        finally:
            session_event_bus.unsubscribe(q)

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/sessions")
async def list_sessions(
    status: str | None = Query(None),
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    sessions = db.query(Session).filter(Session.user_id == user.id).all()
    result = [
        {
            "session_key": s.session_key,
            "name": s.name,
            "created_at": s.created_at.isoformat(),
            "status": "idle",
            "model": s.model,
            "project_path": s.project_path,
            "interactive": s.interactive,
            "claude_session_id": s.claude_session_id,
        }
        for s in sessions
    ]
    if status:
        result = [s for s in result if s["status"] == status]
    return {"sessions": result, "total": len(result)}


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
    return {
        "session_key": session.session_key,
        "name": session.name,
        "status": "idle",
        "model": session.model,
        "project_path": session.project_path,
        "interactive": session.interactive,
        "claude_session_id": session.claude_session_id,
        "created_at": session.created_at.isoformat(),
    }


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
    db.delete(session)
    db.commit()


@router.post("/sessions/{session_key}/messages")
async def send_message(
    session_key: str,
    content: str = Form(...),
    files: list[UploadFile] = File(default=[]),
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.query(Session).filter(
        Session.session_key == session_key, Session.user_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.add(SessionMessage(session_id=session.id, role="user", content=content))
    db.commit()

    # Read uploaded files into memory for forwarding to slave
    file_tuples = None
    if files:
        file_tuples = []
        for f in files:
            data = await f.read()
            file_tuples.append((f.filename or "file", data, f.content_type or "application/octet-stream"))

    result = await slave.run(
        session_key=session_key,
        message=content,
        project_path=session.project_path,
        model=session.model,
        claude_session_id=session.claude_session_id,
        interactive=session.interactive,
        files=file_tuples,
    )

    response_text = (result.get("result") or result.get("error") or "").strip()
    new_claude_sid = result.get("session_id")
    if new_claude_sid:
        session.claude_session_id = new_claude_sid
    db.add(SessionMessage(session_id=session.id, role="assistant", content=response_text))
    db.commit()

    if user.fcm_token and user.notify_sessions and response_text:
        preview = response_text[:100] + ("..." if len(response_text) > 100 else "")
        send_push(user.fcm_token, session.name or "Session reply", preview, {"session_key": session_key})

    return {
        "role": "assistant",
        "content": response_text,
        "session_id": new_claude_sid,
        "cost_usd": result.get("cost_usd"),
    }


@router.post("/sessions/{session_key}/cancel")
async def cancel_session(
    session_key: str,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    session = db.query(Session).filter(
        Session.session_key == session_key, Session.user_id == user.id
    ).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return await slave.cancel(session_key)


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
