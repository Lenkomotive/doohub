import logging
from collections import deque
from datetime import datetime, timezone


class LogBuffer(logging.Handler):
    """In-memory ring buffer that captures log records for the /logs endpoint."""

    def __init__(self, capacity: int = 500):
        super().__init__()
        self._buffer: deque[dict] = deque(maxlen=capacity)

    def emit(self, record: logging.LogRecord) -> None:
        self._buffer.append({
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": self.format(record),
        })

    def get_logs(self, limit: int = 100, level: str | None = None) -> list[dict]:
        entries = list(self._buffer)
        if level:
            entries = [e for e in entries if e["level"] == level.upper()]
        return entries[-limit:]


log_buffer = LogBuffer()
