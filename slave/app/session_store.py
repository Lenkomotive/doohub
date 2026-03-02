import asyncio
import json
import logging

from app.config import settings
from app.event_bus import event_bus

logger = logging.getLogger(__name__)

STORE_FILE = settings.data_dir / "sessions.json"


class SessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, dict] = {}
        self._load()
        self._reset_stale_busy()

    def _load(self) -> None:
        if STORE_FILE.exists():
            try:
                self._sessions = json.loads(STORE_FILE.read_text())
                logger.info("Loaded %d sessions from disk", len(self._sessions))
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Failed to load sessions: %s", e)

    def _reset_stale_busy(self) -> None:
        """Reset sessions left busy from a crash. Called once on startup only."""
        changed = False
        for sid, info in self._sessions.items():
            if info.get("status") == "busy":
                info["status"] = "idle"
                logger.info("Reset stale busy session: %s", sid)
                changed = True
        if changed:
            self._save()

    def _save(self) -> None:
        try:
            STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
            STORE_FILE.write_text(json.dumps(self._sessions, indent=2))
        except OSError as e:
            logger.warning("Failed to save sessions: %s", e)

    def add(self, session_key: str, project_path: str, model: str = "claude-opus-4-6") -> None:
        self._sessions[session_key] = {
            "project_path": project_path,
            "model": model,
            "status": "idle",
            "claude_session_id": None,
            "interactive": False,
        }
        self._save()

    def remove(self, session_key: str) -> None:
        self._sessions.pop(session_key, None)
        self._save()

    def get(self, session_key: str) -> dict | None:
        return self._sessions.get(session_key)

    def list_all(self) -> dict[str, dict]:
        return dict(self._sessions)

    def set_status(self, session_key: str, status: str) -> None:
        if session_key not in self._sessions:
            return
        self._sessions[session_key]["status"] = status
        self._save()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                loop.create_task(event_bus.publish({
                    "event": "status",
                    "session_key": session_key,
                    "status": status,
                }))
        except RuntimeError:
            pass

    def set_claude_session_id(self, session_key: str, claude_session_id: str) -> None:
        if session_key in self._sessions:
            self._sessions[session_key]["claude_session_id"] = claude_session_id
            self._save()

    def set_interactive(self, session_key: str, interactive: bool) -> None:
        if session_key in self._sessions:
            self._sessions[session_key]["interactive"] = interactive
            self._save()


store = SessionStore()
