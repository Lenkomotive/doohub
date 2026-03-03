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
