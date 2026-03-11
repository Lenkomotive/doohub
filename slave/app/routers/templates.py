"""Template proxy — unauthenticated local endpoints for Claude to use.

Forwards requests to the backend's internal template endpoints using the slave API key.
"""

import logging

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/templates")


async def _forward(method: str, path: str, **kwargs) -> dict | list:
    url = f"{settings.backend_url}{path}"
    headers = {"X-API-Key": settings.api_key}
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.request(method, url, headers=headers, **kwargs)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Backend unreachable: {e}")
    if resp.status_code >= 400:
        try:
            detail = resp.json().get("detail", resp.text)
        except Exception:
            detail = resp.text
        raise HTTPException(status_code=resp.status_code, detail=detail)
    if resp.status_code == 204:
        return {}
    return resp.json()


@router.get("")
async def list_templates():
    return await _forward("GET", "/internal/pipeline-templates")


@router.get("/{template_id}")
async def get_template(template_id: int):
    return await _forward("GET", f"/internal/pipeline-templates/{template_id}")


class CreateBody(BaseModel):
    name: str
    description: str | None = None
    definition: dict


class UpdateBody(BaseModel):
    name: str | None = None
    description: str | None = None
    definition: dict | None = None


@router.post("", status_code=201)
async def create_template(body: CreateBody):
    return await _forward("POST", "/internal/pipeline-templates", json=body.model_dump())


@router.put("/{template_id}")
async def update_template(template_id: int, body: UpdateBody):
    return await _forward(
        "PUT",
        f"/internal/pipeline-templates/{template_id}",
        json=body.model_dump(exclude_none=True),
    )
