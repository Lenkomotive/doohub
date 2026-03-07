import asyncio
import collections
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def classify_event(event: dict) -> str:
    """Classify a pipeline event dict into a typed event name."""
    step = event.get("step")
    if isinstance(step, dict):
        step_status = step.get("status")
        if step_status == "running":
            return "pipeline:node_started"
        if step_status == "completed":
            return "pipeline:node_completed"
        if step_status == "failed":
            return "pipeline:node_failed"

    status = event.get("status")
    if status == "done":
        return "pipeline:done"
    if status == "failed":
        return "pipeline:failed"
    if status == "cancelled":
        return "pipeline:cancelled"

    if event.get("previous_status") == "planning":
        return "pipeline:started"

    return "pipeline:status"


class PipelineEventBus:
    """Pub/sub for pipeline status updates. Subscribers get all pipeline events."""

    def __init__(self) -> None:
        self._queues: list[asyncio.Queue] = []
        self._buffer: collections.deque = collections.deque(maxlen=100)

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._queues.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        try:
            self._queues.remove(q)
        except ValueError:
            pass

    async def publish(self, event: dict) -> None:
        event.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        event.setdefault("event_type", classify_event(event))
        self._buffer.append(event)
        for q in list(self._queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("PipelineEventBus: subscriber queue full, dropping event")

    def get_recent(self, pipeline_key: str | None = None, limit: int = 50) -> list[dict]:
        events = list(self._buffer)
        if pipeline_key is not None:
            events = [e for e in events if e.get("pipeline_key") == pipeline_key]
        return events[-limit:]


pipeline_events = PipelineEventBus()
