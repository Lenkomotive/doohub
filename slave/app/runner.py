"""In-memory runner — tracks busy sessions and runs Claude as background tasks.

The slave is fully stateless (no disk persistence). All session config is
passed by the caller with each request. Status is tracked in-memory only
and published to the EventBus so SSE consumers stay up to date.
"""
import asyncio
import logging

from app import claude_runner
from app.event_bus import event_bus

logger = logging.getLogger(__name__)

# session_key -> Queue for the SSE consumer to read from
_runs: dict[str, asyncio.Queue] = {}


async def _set_status(key: str, status: str) -> None:
    await event_bus.publish({"event": "status", "session_key": key, "status": status})


def busy_keys() -> set[str]:
    return set(_runs.keys())


def get_queue(key: str) -> asyncio.Queue | None:
    return _runs.get(key)


async def start_run(
    key: str,
    message: str,
    project_path: str,
    model: str,
    claude_session_id: str | None,
    interactive: bool,
    timeout: int,
) -> asyncio.Queue:
    """Launch Claude as an independent background task. Returns a Queue the
    SSE endpoint reads. Disconnecting the SSE client does NOT cancel Claude."""
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _runs[key] = q

    async def _task() -> None:
        await _set_status(key, "busy")
        try:
            async for event in claude_runner.stream_prompt(
                prompt=message,
                project_path=project_path,
                model=model,
                claude_session_id=claude_session_id,
                timeout=timeout,
                session_key=key,
                interactive=interactive,
            ):
                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning("Queue full for %s, dropping event", key)
                if event.get("event") in ("done", "error"):
                    await event_bus.publish(event)
        except Exception as e:
            err = {"event": "error", "session_key": key, "error": str(e)}
            try:
                q.put_nowait(err)
            except asyncio.QueueFull:
                pass
            await event_bus.publish(err)
        finally:
            _runs.pop(key, None)
            await _set_status(key, "idle")

    asyncio.create_task(_task(), name=f"run-{key}")
    return q
