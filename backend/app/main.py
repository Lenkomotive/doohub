# FastAPI application entry point for the DooHub backend.
# Initializes the app, configures CORS middleware, registers routers
# (auth, sessions, pipelines, pipeline_templates), and exposes a /health endpoint.

import asyncio
import logging
import os
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.log_buffer import log_buffer
from app.core.slave_client import _session_event_consumer, slave
from app.models.pipeline_template import PipelineTemplate
from app.models.user import User
from app.routers import auth, pipeline_templates, pipelines, sessions

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
# Attach the in-memory buffer to the root logger so it captures everything
log_buffer.setFormatter(logging.Formatter("%(name)s: %(message)s"))
logging.getLogger().addHandler(log_buffer)

logger = logging.getLogger(__name__)
req_logger = logging.getLogger("doohub.requests")

DEFAULT_TEMPLATE_DEFINITION = {
    "name": "Default Plan-Develop-Review",
    "nodes": [
        {
            "id": "start",
            "type": "start",
            "name": "Start",
            "position": {"x": 0, "y": 0},
        },
        {
            "id": "planner",
            "type": "claude_agent",
            "name": "Planner",
            "prompt_template": (
                "You are a PLANNER. Analyze the issue and create a detailed implementation plan.\n"
                "Issue: {{issue_title}}\n{{issue_body}}"
            ),
            "model": None,
            "timeout": 600,
            "retry": {"max_attempts": 1},
            "outputs": ["plan"],
            "requires": [],
            "extract": {},
            "status_label": "planning",
            "position": {"x": 0, "y": 150},
        },
        {
            "id": "developer",
            "type": "claude_agent",
            "name": "Developer",
            "prompt_template": (
                "You are a DEVELOPER. Implement the changes according to the plan.\n"
                "## Plan\n{{plan}}"
            ),
            "model": None,
            "timeout": 600,
            "retry": {"max_attempts": 1},
            "outputs": ["pr_url"],
            "requires": ["plan"],
            "extract": {"pr_url": r"regex:https://github\.com/[^\s)]+/pull/\d+"},
            "status_label": "developing",
            "position": {"x": 0, "y": 300},
        },
        {
            "id": "reviewer",
            "type": "claude_agent",
            "name": "Reviewer",
            "prompt_template": "Review PR #{{pr_number}} for correctness and quality.",
            "model": None,
            "timeout": 600,
            "retry": {"max_attempts": 1},
            "outputs": ["verdict"],
            "requires": ["pr_url"],
            "extract": {"verdict": "keyword:APPROVED|CHANGES_REQUESTED"},
            "status_label": "reviewing",
            "position": {"x": 0, "y": 450},
        },
        {
            "id": "verdict_check",
            "type": "condition",
            "name": "Verdict Check",
            "condition_field": "verdict",
            "branches": {"APPROVED": "done", "CHANGES_REQUESTED": "developer"},
            "default_branch": "fail",
            "max_iterations": 3,
            "iteration_counter": "review_round",
            "position": {"x": 0, "y": 600},
        },
        {
            "id": "done",
            "type": "end",
            "name": "Done",
            "status": "done",
            "position": {"x": 0, "y": 750},
        },
        {
            "id": "fail",
            "type": "end",
            "name": "Failed",
            "status": "failed",
            "position": {"x": 200, "y": 750},
        },
    ],
    "edges": [
        {"from": "start", "to": "planner"},
        {"from": "planner", "to": "developer"},
        {"from": "developer", "to": "reviewer"},
        {"from": "reviewer", "to": "verdict_check"},
    ],
}


def _seed_default_template() -> None:
    db = SessionLocal()
    try:
        existing = db.query(PipelineTemplate).filter_by(name="Default Plan-Develop-Review").first()
        if not existing:
            template = PipelineTemplate(
                name="Default Plan-Develop-Review",
                description="Default pipeline: plan → develop → review loop with up to 3 review rounds.",
                definition=DEFAULT_TEMPLATE_DEFINITION,
            )
            db.add(template)
            db.commit()
            logger.info("Seeded default pipeline template")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    _seed_default_template()
    task = asyncio.create_task(_session_event_consumer())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


app = FastAPI(title=settings.app_name, lifespan=lifespan)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000)
        # Extract session key from path if present (e.g. /sessions/{key}/messages)
        path = request.url.path
        parts = path.strip("/").split("/")
        session_key = parts[1] if len(parts) >= 2 and parts[0] == "sessions" else ""
        extra = f" session={session_key}" if session_key else ""
        req_logger.info(
            "%s %s %s %dms [rid=%s]%s",
            request.method, path, response.status_code,
            duration_ms, request_id, extra,
        )
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestLoggingMiddleware)

cors_origins = ["http://localhost:3000"]
if os.environ.get("DOOHUB_CORS_ORIGIN"):
    cors_origins.append(os.environ["DOOHUB_CORS_ORIGIN"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://doohub.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(pipelines.router)
app.include_router(pipeline_templates.router)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/logs")
async def get_logs(
    limit: int = 100,
    level: str | None = None,
    _user: User = Depends(get_current_user),
):
    backend_logs = log_buffer.get_logs(limit=limit, level=level)
    # Also fetch slave logs
    slave_logs = []
    try:
        slave_data = await slave.get_logs(limit=limit, level=level)
        slave_logs = slave_data.get("logs", [])
    except Exception:
        pass
    return {"backend": backend_logs, "slave": slave_logs}
