import logging
import time

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.log_buffer import log_buffer
from app.routers import orchestrate, repos, run, templates

logging.basicConfig(
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
)
log_buffer.setFormatter(logging.Formatter("%(name)s: %(message)s"))
logging.getLogger().addHandler(log_buffer)

req_logger = logging.getLogger("slave.requests")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", "-")
        request.state.request_id = request_id
        start = time.monotonic()
        response = await call_next(request)
        duration_ms = round((time.monotonic() - start) * 1000)
        req_logger.info(
            "%s %s %s %dms [rid=%s]",
            request.method, request.url.path, response.status_code,
            duration_ms, request_id,
        )
        return response


app = FastAPI(title="DooHub Slave", version="1.0.0")

app.add_middleware(RequestLoggingMiddleware)

app.include_router(run.router)
app.include_router(repos.router)
app.include_router(orchestrate.router)
app.include_router(templates.router)


@app.get("/api/health")
async def health():
    return {"status": "ok"}


@app.get("/api/logs")
async def get_logs(limit: int = 100, level: str | None = None):
    return {"logs": log_buffer.get_logs(limit=limit, level=level)}
