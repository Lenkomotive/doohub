import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import settings

logger = logging.getLogger(__name__)


class SlaveClient:
    """HTTP client that proxies requests to the slave service."""

    def __init__(self) -> None:
        self.base_url = settings.slave_url.rstrip("/")
        self.headers = {"X-API-Key": settings.slave_api_key}

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self.base_url,
            headers=self.headers,
            timeout=httpx.Timeout(300.0, connect=10.0),
        )

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        try:
            async with self._client() as client:
                resp = await client.request(method, path, **kwargs)
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="Slave service is unreachable")
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Slave request timed out")
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Slave error: {exc}")

        if resp.status_code >= 400:
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise HTTPException(status_code=resp.status_code, detail=detail)

        if resp.status_code == 204:
            return None

        return resp.json()

    async def _stream_sse(self, method: str, path: str, **kwargs: Any) -> AsyncGenerator[dict, None]:
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
        except httpx.ConnectError:
            raise HTTPException(status_code=502, detail="Slave service is unreachable")
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f"Slave error: {exc}")

    async def run(
        self,
        session_key: str,
        message: str,
        project_path: str,
        model: str,
        claude_session_id: str | None,
        interactive: bool = False,
        timeout: int = 300,
    ) -> Any:
        return await self._request("POST", "/api/run", json={
            "session_key": session_key,
            "message": message,
            "project_path": project_path,
            "model": model,
            "claude_session_id": claude_session_id,
            "interactive": interactive,
            "timeout": timeout,
        })

    async def stream_events(self) -> AsyncGenerator[dict, None]:
        async for event in self._stream_sse("GET", "/api/events"):
            yield event

    async def cancel(self, key: str) -> Any:
        return await self._request("POST", f"/api/cancel/{key}")

    async def list_repos(self) -> Any:
        return await self._request("GET", "/api/repos")

    async def start_pipeline(
        self,
        pipeline_key: str,
        repo_path: str,
        issue_number: int | None,
        task_description: str | None,
        model: str,
        callback_url: str,
    ) -> Any:
        return await self._request("POST", "/api/orchestrate", json={
            "pipeline_key": pipeline_key,
            "repo_path": repo_path,
            "issue_number": issue_number,
            "task_description": task_description,
            "model": model,
            "callback_url": callback_url,
        })

    async def cancel_pipeline(self, pipeline_key: str) -> Any:
        return await self._request("POST", f"/api/orchestrate/{pipeline_key}/cancel")

    async def fetch_issue(self, repo_path: str, issue_number: int) -> Any:
        return await self._request("GET", "/api/repos/issue", params={
            "repo_path": repo_path,
            "issue_number": issue_number,
        })


slave = SlaveClient()
