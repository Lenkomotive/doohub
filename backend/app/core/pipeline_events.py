import asyncio
import logging

logger = logging.getLogger(__name__)


class PipelineEventBus:
    """Pub/sub for pipeline status updates. Subscribers get all pipeline events."""

    def __init__(self) -> None:
        self._queues: list[asyncio.Queue] = []

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
        for q in list(self._queues):
            try:
                q.put_nowait(event)
            except asyncio.QueueFull:
                logger.warning("PipelineEventBus: subscriber queue full, dropping event")


pipeline_events = PipelineEventBus()
