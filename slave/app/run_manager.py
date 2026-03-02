"""Background task manager for Claude runs.

Each call to start_run() launches Claude as an independent asyncio Task that
is completely decoupled from the HTTP connection. The SSE endpoint reads from
a per-session Queue; when the client disconnects (e.g. navigating away), only
the SSE consumer is cancelled — Claude keeps running. When the task finishes,
set_status("idle") fires automatically, which notifies SessionsCubit via the
EventBus.
"""
import asyncio
import logging

from app import claude_runner
from app.event_bus import EventBus
from app.session_store import SessionStore

logger = logging.getLogger(__name__)

# Per-session queues. Key = session_key, value = Queue the SSE consumer reads.
_runs: dict[str, asyncio.Queue] = {}


async def start_run(
    key: str,
    session: dict,
    store: SessionStore,
    bus: EventBus,
    message: str,
    timeout: int = 300,
) -> asyncio.Queue:
    """Start a Claude run as a background task.

    Returns a Queue that the SSE endpoint reads to forward events to the client.
    The Task outlives any HTTP connection — safe to disconnect and reconnect.
    """
    q: asyncio.Queue = asyncio.Queue(maxsize=200)
    _runs[key] = q

    async def _task() -> None:
        try:
            async for event in claude_runner.stream_prompt(
                prompt=message,
                project_path=session["project_path"],
                model=session.get("model", "claude-opus-4-6"),
                claude_session_id=session.get("claude_session_id"),
                timeout=timeout,
                session_key=key,
                interactive=session.get("interactive", False),
            ):
                evt = event.get("event")
                if evt == "done":
                    new_sid = event.get("session_id")
                    if new_sid:
                        store.set_claude_session_id(key, new_sid)
                    await bus.publish(event)
                elif evt == "error":
                    await bus.publish(event)

                try:
                    q.put_nowait(event)
                except asyncio.QueueFull:
                    logger.warning("Run queue full for %s, dropping token", key)

        except Exception as e:
            err = {"event": "error", "session_key": key, "error": str(e)}
            try:
                q.put_nowait(err)
            except asyncio.QueueFull:
                pass
            await bus.publish(err)
        finally:
            _runs.pop(key, None)
            store.set_status(key, "idle")

    asyncio.create_task(_task(), name=f"claude-run-{key}")
    return q


def get_queue(key: str) -> asyncio.Queue | None:
    """Return the active run queue for a session, if one exists."""
    return _runs.get(key)
