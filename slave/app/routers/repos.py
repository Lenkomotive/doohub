import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_api_key
from app.config import settings

router = APIRouter(prefix="/api/repos", dependencies=[Depends(require_api_key)])


@router.get("")
async def list_repos():
    """List git repositories in the projects directory."""
    projects = settings.projects_dir
    if not projects.exists():
        return {"repos": []}
    repos = [
        {"name": entry.name, "path": str(entry)}
        for entry in sorted(projects.iterdir())
        if entry.is_dir() and (entry / ".git").exists()
    ]
    return {"repos": repos}


@router.get("/issues")
async def list_issues(
    repo_path: str = Query(...),
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
):
    """List open GitHub issues for a repository via the gh CLI."""
    # Fetch one extra to detect if there are more pages
    fetch_limit = page * per_page + 1
    proc = await asyncio.create_subprocess_exec(
        "gh", "issue", "list",
        "--state", "open",
        "--limit", str(fetch_limit),
        "--json", "number,title,labels,state",
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
    if proc.returncode != 0:
        raise HTTPException(
            status_code=502,
            detail=f"gh issue list failed: {stderr.decode().strip()}",
        )
    all_issues = json.loads(stdout.decode())
    start = (page - 1) * per_page
    page_issues = all_issues[start : start + per_page]
    has_more = len(all_issues) > start + per_page
    return {"issues": page_issues, "has_more": has_more, "page": page}


@router.get("/issue")
async def get_issue(
    repo_path: str = Query(...),
    issue_number: int = Query(...),
):
    """Fetch a GitHub issue via the gh CLI."""
    proc = await asyncio.create_subprocess_exec(
        "gh", "issue", "view", str(issue_number),
        "--json", "number,title,body,labels,state",
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
    if proc.returncode != 0:
        raise HTTPException(
            status_code=502,
            detail=f"gh issue view failed: {stderr.decode().strip()}",
        )
    return json.loads(stdout.decode())
