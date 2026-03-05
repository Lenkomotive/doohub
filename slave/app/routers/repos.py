import asyncio
import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.auth import require_api_key
from app.config import settings

router = APIRouter(prefix="/api/repos", dependencies=[Depends(require_api_key)])

_ISSUES_QUERY = """
query($owner: String!, $name: String!, $first: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    issues(first: $first, after: $after, states: OPEN, orderBy: {field: CREATED_AT, direction: DESC}) {
      pageInfo { hasNextPage endCursor }
      nodes {
        number
        title
        labels(first: 10) { nodes { name } }
      }
    }
  }
}
"""


async def _get_repo_nwo(repo_path: str) -> str:
    """Get owner/name for a repo using gh."""
    proc = await asyncio.create_subprocess_exec(
        "gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner",
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=10)
    if proc.returncode != 0:
        raise HTTPException(status_code=502, detail="Failed to determine repo owner/name")
    return stdout.decode().strip()


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
    per_page: int = Query(30, ge=1, le=100),
    cursor: Optional[str] = Query(None),
):
    """List open GitHub issues with cursor-based pagination via GraphQL."""
    nwo = await _get_repo_nwo(repo_path)
    owner, name = nwo.split("/", 1)

    cmd = [
        "gh", "api", "graphql",
        "-F", f"query={_ISSUES_QUERY}",
        "-F", f"owner={owner}",
        "-F", f"name={name}",
        "-F", f"first={per_page}",
    ]
    if cursor:
        cmd += ["-F", f"after={cursor}"]

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=repo_path,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
    if proc.returncode != 0:
        raise HTTPException(
            status_code=502,
            detail=f"GraphQL query failed: {stderr.decode().strip()}",
        )

    data = json.loads(stdout.decode())
    repo_data = data.get("data", {}).get("repository", {}).get("issues", {})
    page_info = repo_data.get("pageInfo", {})
    nodes = repo_data.get("nodes", [])

    issues = [
        {
            "number": n["number"],
            "title": n["title"],
            "labels": [{"name": l["name"]} for l in n.get("labels", {}).get("nodes", [])],
        }
        for n in nodes
    ]

    return {
        "issues": issues,
        "has_more": page_info.get("hasNextPage", False),
        "end_cursor": page_info.get("endCursor"),
    }


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
