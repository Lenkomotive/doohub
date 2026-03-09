import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx
from fastapi import HTTPException

from app.core.config import settings
from app.core.session_events import session_events

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

    async def _request(self, method: str, path: str, request_id: str | None = None, **kwargs: Any) -> Any:
        try:
            headers = kwargs.pop("headers", {})
            if request_id:
                headers["X-Request-ID"] = request_id
            async with self._client() as client:
                resp = await client.request(method, path, headers=headers, **kwargs)
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
        mode: str = "oneshot",
        timeout: int = 300,
        files: list[tuple[str, bytes, str]] | None = None,
    ) -> Any:
        if files:
            multipart_files = [
                ("files", (fname, data, ctype)) for fname, data, ctype in files
            ]
            form_data = {
                "session_key": session_key,
                "message": message,
                "project_path": project_path,
                "model": model,
                "mode": mode,
                "timeout": str(timeout),
            }
            if claude_session_id:
                form_data["claude_session_id"] = claude_session_id
            return await self._request(
                "POST",
                "/api/run/files",
                data=form_data,
                files=multipart_files,
            )
        return await self._request("POST", "/api/run", json={
            "session_key": session_key,
            "message": message,
            "project_path": project_path,
            "model": model,
            "claude_session_id": claude_session_id,
            "mode": mode,
            "timeout": timeout,
        })

    async def stream_run(
        self,
        session_key: str,
        message: str,
        project_path: str,
        model: str,
        claude_session_id: str | None,
        mode: str = "freeform",
        timeout: int = 300,
    ) -> AsyncGenerator[dict, None]:
        """Start a streaming run on the slave. Yields SSE events."""
        async for event in self._stream_sse("POST", "/api/run/stream", json={
            "session_key": session_key,
            "message": message,
            "project_path": project_path,
            "model": model,
            "claude_session_id": claude_session_id,
            "mode": mode,
            "timeout": timeout,
        }):
            yield event

    async def stream_events(self) -> AsyncGenerator[dict, None]:
        async for event in self._stream_sse("GET", "/api/events"):
            yield event

    async def cancel(self, key: str) -> Any:
        return await self._request("POST", f"/api/sessions/{key}/cancel")

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
        template_definition: dict,
        nested_templates: dict | None = None,
    ) -> Any:
        payload: dict[str, Any] = {
            "pipeline_key": pipeline_key,
            "repo_path": repo_path,
            "issue_number": issue_number,
            "task_description": task_description,
            "model": model,
            "callback_url": callback_url,
            "template_definition": template_definition,
        }
        if nested_templates:
            payload["nested_templates"] = nested_templates
        return await self._request("POST", "/api/orchestrate", json=payload)

    async def cancel_pipeline(self, pipeline_key: str) -> Any:
        return await self._request("POST", f"/api/orchestrate/{pipeline_key}/cancel")

    async def cleanup_pipeline(
        self, pipeline_key: str, repo_path: str,
        branch: str | None = None, pr_number: int | None = None,
    ) -> Any:
        return await self._request("POST", f"/api/orchestrate/{pipeline_key}/cleanup", json={
            "repo_path": repo_path,
            "branch": branch,
            "pr_number": pr_number,
        })

    async def check_merge_status(self, repo_path: str, pr_number: int) -> Any:
        return await self._request("GET", "/api/orchestrate/merge-status", params={
            "repo_path": repo_path,
            "pr_number": pr_number,
        })

    async def merge_pipeline(self, pipeline_key: str, repo_path: str, pr_number: int) -> Any:
        return await self._request("POST", f"/api/orchestrate/{pipeline_key}/merge", json={
            "repo_path": repo_path,
            "pr_number": pr_number,
        })

    async def resolve_conflicts(
        self, pipeline_key: str, repo_path: str, branch: str, model: str,
    ) -> Any:
        return await self._request(
            "POST", f"/api/orchestrate/{pipeline_key}/resolve-conflicts",
            json={"repo_path": repo_path, "branch": branch, "model": model},
        )

    async def list_issues(self, repo_path: str, per_page: int = 30, cursor: str | None = None) -> Any:
        params: dict = {"repo_path": repo_path, "per_page": per_page}
        if cursor:
            params["cursor"] = cursor
        return await self._request("GET", "/api/repos/issues", params=params)

    async def fetch_issue(self, repo_path: str, issue_number: int) -> Any:
        return await self._request("GET", "/api/repos/issue", params={
            "repo_path": repo_path,
            "issue_number": issue_number,
        })

    async def generate_name(self) -> str:
        try:
            data = await self._request("POST", "/api/generate-name")
            return data.get("name", "New Session")
        except Exception:
            return "New Session"

    async def get_logs(self, limit: int = 100, level: str | None = None) -> Any:
        params: dict = {"limit": limit}
        if level:
            params["level"] = level
        return await self._request("GET", "/api/logs", params=params)


slave = SlaveClient()


async def _session_event_consumer() -> None:
    """Background task: consume slave SSE events and publish to SessionEventBus."""
    while True:
        try:
            async for event in slave.stream_events():
                await session_events.publish(event)
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Session event stream disconnected, reconnecting in 5s")
        await asyncio.sleep(5)
