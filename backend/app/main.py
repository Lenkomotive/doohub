import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import auth, pipelines, sessions

app = FastAPI(title=settings.app_name)

cors_origins = ["http://localhost:3000"]
if os.environ.get("DOOHUB_CORS_ORIGIN"):
    cors_origins.append(os.environ["DOOHUB_CORS_ORIGIN"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
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
