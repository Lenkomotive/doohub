# FastAPI application entry point for the DooHub backend.
# Initializes the app, configures CORS middleware, registers routers
# (auth, sessions, pipelines, pipeline_templates), and exposes a /health endpoint.

import asyncio
import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.slave_client import _session_event_consumer
from app.models.pipeline_template import PipelineTemplate
from app.routers import auth, pipeline_templates, pipelines, sessions

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_TEMPLATE_DEFINITION = {
    "version": "1.0",
    "name": "Default Plan-Develop-Review",
    "nodes": [
        {"id": "start", "type": "start"},
        {"id": "plan", "type": "claude_agent", "prompt": "Analyze the issue and create an implementation plan."},
        {"id": "develop", "type": "claude_agent", "prompt": "Implement the changes according to the plan."},
        {"id": "review", "type": "claude_agent", "prompt": "Review the implementation for correctness and quality."},
        {"id": "end", "type": "end"},
    ],
    "edges": [
        {"from": "start", "to": "plan"},
        {"from": "plan", "to": "develop"},
        {"from": "develop", "to": "review"},
        {"from": "review", "to": "end"},
    ],
}


def _seed_default_template() -> None:
    db = SessionLocal()
    try:
        existing = db.query(PipelineTemplate).filter_by(name="Default Plan-Develop-Review").first()
        if not existing:
            template = PipelineTemplate(
                name="Default Plan-Develop-Review",
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
