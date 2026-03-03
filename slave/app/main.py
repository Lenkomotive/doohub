import logging

from fastapi import FastAPI

from app.routers import orchestrate, repos, run

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=logging.INFO,
)

app = FastAPI(title="DooHub Slave", version="1.0.0")

app.include_router(run.router)
app.include_router(repos.router)
app.include_router(orchestrate.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
