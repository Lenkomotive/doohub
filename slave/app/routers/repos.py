from fastapi import APIRouter, Depends

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
