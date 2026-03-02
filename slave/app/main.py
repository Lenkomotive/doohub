import logging

from fastapi import FastAPI

from app.routers import repos, sessions

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)

app = FastAPI(title="DooHub Slave", version="1.0.0")

app.include_router(sessions.router)
app.include_router(repos.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
