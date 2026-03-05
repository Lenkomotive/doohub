# FastAPI application entry point for the DooHub backend.
# Initializes the app, configures CORS middleware, registers routers
# (auth, sessions, pipelines), and exposes a /health endpoint.
# test: vercel should skip this v4

import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.slave_client import _session_event_consumer
from app.routers import auth, pipelines, sessions


@asynccontextmanager
async def lifespan(app: FastAPI):
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


@app.get("/health")
def health():
    return {"status": "ok"}
