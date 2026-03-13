"""In-memory runner — tracks busy sessions.

The slave is fully stateless (no disk persistence). All session config is
passed by the caller with each request. Status is tracked in-memory only
and published to the EventBus so SSE consumers stay up to date.
"""
import logging

from app.event_bus import event_bus

logger = logging.getLogger(__name__)

# session_key set of currently busy sessions
_busy: set[str] = set()


async def _set_status(key: str, status: str) -> None:
    if status == "busy":
        _busy.add(key)
    else:
        _busy.discard(key)
    await event_bus.publish({"event": "status", "session_key": key, "status": status})


def busy_keys() -> set[str]:
    return set(_busy)
