import logging
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
        """Make an HTTP request to the provider and return parsed JSON.

        Raises HTTPException with appropriate status on failure.
        """
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
            # Forward the provider's error to the caller
            try:
                detail = resp.json().get("detail", resp.text)
            except Exception:
                detail = resp.text
            raise HTTPException(status_code=resp.status_code, detail=detail)

        # 204 No Content
        if resp.status_code == 204:
            return None

        return resp.json()

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

    async def cancel_session(self, key: str) -> Any:
        return await self._request("POST", f"/api/sessions/{key}/cancel")

    # --- Repos ---

    async def list_repos(self) -> Any:
        return await self._request("GET", "/api/repos")


provider = ProviderClient()
