import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


class ProviderClient:
    """HTTP client that proxies requests to the dooslave provider API."""

    def __init__(self) -> None:
        self.base_url = settings.provider_url.rstrip("/")
        self.headers = {"X-API-Key": settings.provider_api_key}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=httpx.Timeout(300.0, connect=10.0),
        )

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Make an HTTP request to the provider and return parsed JSON."""
        try:
            async with self._client() as client:
                resp = await client.request(method, path, **kwargs)
        except httpx.ConnectError:
            logger.error("Provider unreachable at %s", self.base_url)
            raise HTTPException(
                status_code=502, detail="Provider service is unreachable"
            )
        except httpx.TimeoutException:
            logger.error("Provider request timed out: %s %s", method, path)
            raise HTTPException(
                status_code=504, detail="Provider request timed out"
            )
        except httpx.HTTPError as exc:
            logger.error("Provider HTTP error: %s", exc)
            raise HTTPException(
                status_code=502, detail=f"Provider error: {exc}"
            )

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise HTTPException(status_code=resp.status_code, detail=detail)

        if resp.status_code == 204:
            return None

        return resp.json()

    async def _stream_sse(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> AsyncGenerator[dict, None]:
        """Open an SSE connection to dooslave and yield parsed event dicts."""
        stream_headers = {**self.headers, "Accept": "text/event-stream"}
        try:
            async with httpx.AsyncClient(
                base_url=self.base_url,
                headers=stream_headers,
                timeout=httpx.Timeout(None, connect=10.0),
            ) as client:
                async with client.stream(method, path, **kwargs) as resp:
                    if resp.status_code >= 400:
                        body = await resp.aread()
                        try:
                            detail = json.loads(body).get("detail", body.decode())
                        except Exception:
                            detail = body.decode()
                        raise HTTPException(status_code=resp.status_code, detail=detail)

                    event_type = "message"
                    async for raw_line in resp.aiter_lines():
                        if raw_line.startswith("event:"):
                            event_type = raw_line[len("event:"):].strip()
                        elif raw_line.startswith("data:"):
                            data_str = raw_line[len("data:"):].strip()
                            try:
                                yield {"event": event_type, **json.loads(data_str)}
                            except json.JSONDecodeError:
                                pass
                            event_type = "message"
                        # skip keepalive comment lines
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="Provider service is unreachable")
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Provider error: {exc}")

    # --- Sessions ---

    async def list_sessions(self) -> Any:
        return await self._request("GET", "/api/sessions")

    async def create_session(
        self,
        key: str,
        model: str = "sonnet",
        path: str = "/projects",
        interactive: bool = False,
    ) -> Any:
        return await self._request(
            "POST",
            "/api/sessions",
            json={
                "session_key": key,
                "model": model,
                "project_path": path,
                "interactive": interactive,
            },
        )

    async def get_session(self, key: str) -> Any:
        return await self._request("GET", f"/api/sessions/{key}")

    async def delete_session(self, key: str) -> Any:
        return await self._request("DELETE", f"/api/sessions/{key}")

    async def send_message(self, key: str, content: str) -> Any:
        return await self._request(
            "POST",
            f"/api/sessions/{key}/message",
            json={"message": content},
        )

    async def stream_events(self) -> AsyncGenerator[dict, None]:
        """SSE stream of status events for all sessions."""
        async for event in self._stream_sse("GET", "/api/sessions/events"):
            yield event

    async def stream_message(self, key: str, content: str) -> AsyncGenerator[dict, None]:
        """SSE stream of token/done events for a single session message."""
        async for event in self._stream_sse(
            "POST",
            f"/api/sessions/{key}/message/stream",
            json={"message": content},
        ):
            yield event

    async def cancel_session(self, key: str) -> Any:
        return await self._request("POST", f"/api/sessions/{key}/cancel")

    # --- Repos ---

    async def list_repos(self) -> Any:
        return await self._request("GET", "/api/repos")


provider = ProviderClient()
