"""Pipeline orchestrator — graph-based template executor.

Triggered on-demand via HTTP. Reports progress to backend via callbacks.
Tracks running pipelines in memory only (backend owns persistent state).
"""
import asyncio
import json
import logging
import re
import shutil
from pathlib import Path

import httpx

from app.config import settings
from app.graph_executor import execute_graph

logger = logging.getLogger(__name__)

WORKTREE_DIR = settings.data_dir / "worktrees"

# pipeline_key -> asyncio.Task
_tasks: dict[str, asyncio.Task] = {}


# ── Helpers ──────────────────────────────────────────────────────────────────


async def _run_git(cwd: str, *args: str) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        "git", *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    return proc.returncode, stdout.decode().strip(), stderr.decode().strip()


async def _run_gh(cwd: str, *args: str) -> tuple[int, str]:
    proc = await asyncio.create_subprocess_exec(
        "gh", *args,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
    if proc.returncode != 0:
        logger.warning("gh %s failed: %s", " ".join(args), stderr.decode().strip())
    return proc.returncode, stdout.decode().strip()


async def _callback(url: str, api_key: str, data: dict) -> None:
    """POST a status update to the backend callback URL."""
    for attempt in range(3):
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(
                    url, json=data, headers={"X-API-Key": api_key},
                )
                if resp.status_code < 400:
                    return
                logger.warning("Callback %d: %s", resp.status_code, resp.text)
        except Exception as e:
            logger.warning("Callback attempt %d failed: %s", attempt + 1, e)
        if attempt < 2:
            await asyncio.sleep(2 ** attempt)


def _slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:40]


# ── Worktree ─────────────────────────────────────────────────────────────────


async def _ensure_worktree(repo_path: str, pipeline_key: str, branch: str) -> str | None:
    """Create or reuse a git worktree. Returns the worktree path."""
    slug = re.sub(r"[^a-z0-9]+", "-", pipeline_key.lower()).strip("-")
    worktree_path = str(WORKTREE_DIR / slug)

    # Reuse if valid
    if Path(worktree_path).exists() and (Path(worktree_path) / ".git").exists():
        await _run_git(worktree_path, "fetch", "origin")
        return worktree_path

    await _run_git(repo_path, "fetch", "origin")
    await _run_git(repo_path, "worktree", "prune")

    if Path(worktree_path).exists():
        shutil.rmtree(worktree_path)

    WORKTREE_DIR.mkdir(parents=True, exist_ok=True)

    code, _, err = await _run_git(
        repo_path, "worktree", "add", worktree_path, "-b", branch, "origin/main",
    )
    if code != 0:
        # Branch may exist from a previous attempt
        code, _, err = await _run_git(
            repo_path, "worktree", "add", worktree_path, branch,
        )
        if code != 0:
            logger.error("Failed to create worktree: %s", err)
            return None

    logger.info("Created worktree at %s on branch %s", worktree_path, branch)
    return worktree_path


async def _cleanup_worktree(repo_path: str, worktree_path: str) -> None:
    if not Path(worktree_path).exists():
        return
    await _run_git(repo_path, "worktree", "remove", worktree_path, "--force")
    await _run_git(repo_path, "worktree", "prune")


# ── Cleanup ──────────────────────────────────────────────────────────────────


async def _cancel_cleanup(ctx: dict) -> None:
    """Close PR and remove worktree on cancellation."""
    repo_path = ctx["repo_path"]
    key = ctx["pipeline_key"]

    # Close the PR if one was opened
    pr_number = ctx.get("pr_number")
    if pr_number:
        logger.info("Pipeline %s: closing PR #%d", key, pr_number)
        await _run_gh(
            repo_path, "pr", "close", str(pr_number),
            "--comment", "Pipeline cancelled.",
        )

    # Remove worktree
    branch = ctx.get("branch")
    slug = re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")
    worktree_path = str(WORKTREE_DIR / slug)
    await _cleanup_worktree(repo_path, worktree_path)

    # Delete remote branch
    if branch:
        logger.info("Pipeline %s: deleting branch %s", key, branch)
        await _run_git(repo_path, "push", "origin", "--delete", branch)


# ── Pipeline Executor ────────────────────────────────────────────────────────


async def _run_pipeline(ctx: dict) -> None:
    """Execute a pipeline using the graph executor with a template definition."""
    key = ctx["pipeline_key"]
    cb_url = ctx["callback_url"]
    api_key = ctx["api_key"]
    repo_path = ctx["repo_path"]
    definition = ctx["template_definition"]

    logger.info("Pipeline %s: executing template '%s'", key, definition.get("name", "unnamed"))

    # Always fetch latest issue details from GitHub
    if ctx.get("issue_number"):
        code, out = await _run_gh(
            repo_path, "issue", "view", str(ctx["issue_number"]),
            "--json", "title,body",
        )
        if code == 0 and out:
            try:
                data = json.loads(out)
                ctx["issue_title"] = data.get("title", ctx.get("issue_title", ""))
                ctx["issue_body"] = data.get("body", "")
            except json.JSONDecodeError:
                pass

    # Build branch name
    if ctx.get("issue_number"):
        title_slug = _slugify(ctx.get("issue_title", "task"))
        ctx["branch"] = f"doohub/issue-{ctx['issue_number']}-{title_slug}"
    else:
        ctx["branch"] = f"doohub/pipeline-{key}"

    try:
        # Setup worktree
        worktree_path = await _ensure_worktree(repo_path, key, ctx["branch"])
        if not worktree_path:
            await _callback(cb_url, api_key, {
                "pipeline_key": key, "status": "failed", "error": "Failed to create worktree",
            })
            return

        ctx["worktree_path"] = worktree_path

        # Template loader for nested template nodes
        async def template_loader(template_id: int) -> dict | None:
            base_url = cb_url.rsplit("/pipelines/", 1)[0]
            url = f"{base_url}/pipeline-templates/{template_id}"
            try:
                async with httpx.AsyncClient(timeout=10) as client:
                    resp = await client.get(url, headers={"X-API-Key": api_key})
                    if resp.status_code == 200:
                        return resp.json().get("definition")
                    logger.warning("Template loader: %d returned %d", template_id, resp.status_code)
            except Exception as e:
                logger.error("Template loader failed for %d: %s", template_id, e)
            return None

        ctx["_template_loader"] = template_loader

        # Run the graph
        async def cb(data: dict) -> None:
            await _callback(cb_url, api_key, data)

        await execute_graph(definition, ctx, cb)

        # Cleanup worktree on success
        await _cleanup_worktree(repo_path, worktree_path)

    except asyncio.CancelledError:
        logger.info("Pipeline %s cancelled — cleaning up", key)
        await _cancel_cleanup(ctx)
        await _callback(cb_url, api_key, {
            "pipeline_key": key, "status": "cancelled",
        })
        raise
    except Exception as e:
        logger.error("Pipeline %s error: %s", key, e, exc_info=True)
        slug = re.sub(r"[^a-z0-9]+", "-", key.lower()).strip("-")
        await _cleanup_worktree(repo_path, str(WORKTREE_DIR / slug))
        await _callback(cb_url, api_key, {
            "pipeline_key": key, "status": "failed", "error": str(e),
        })
    finally:
        _tasks.pop(key, None)


# ── Merge Helpers ─────────────────────────────────────────────────────────────


async def check_merge_status(repo_path: str, pr_number: int) -> dict:
    """Check if a PR is mergeable and whether it has conflicts."""
    code, out = await _run_gh(
        repo_path, "pr", "view", str(pr_number),
        "--json", "mergeable,state,mergeStateStatus",
    )
    if code != 0:
        return {"mergeable": False, "has_conflicts": False, "already_merged": False, "error": f"Failed to check PR: {out}"}

    try:
        data = json.loads(out)
    except json.JSONDecodeError:
        return {"mergeable": False, "has_conflicts": False, "already_merged": False, "error": "Failed to parse PR data"}

    state = data.get("state", "").upper()
    mergeable = data.get("mergeable", "").upper()
    merge_state = data.get("mergeStateStatus", "").upper()

    if state == "MERGED":
        return {"mergeable": False, "has_conflicts": False, "already_merged": True, "error": None}
    if state == "CLOSED":
        return {"mergeable": False, "has_conflicts": False, "already_merged": False, "error": "PR is closed"}

    has_conflicts = mergeable == "CONFLICTING" or merge_state == "DIRTY"
    is_mergeable = mergeable == "MERGEABLE" and not has_conflicts

    return {
        "mergeable": is_mergeable,
        "has_conflicts": has_conflicts,
        "already_merged": False,
        "error": None,
    }


async def merge_pr(repo_path: str, pr_number: int) -> dict:
    """Merge a PR using squash merge and delete the branch."""
    code, out = await _run_gh(
        repo_path, "pr", "merge", str(pr_number),
        "--squash", "--delete-branch",
    )
    if code != 0:
        return {"success": False, "error": out or "Merge failed"}
    return {"success": True, "error": None}


# ── Public API ───────────────────────────────────────────────────────────────


def start(
    pipeline_key: str,
    repo_path: str,
    issue_number: int | None,
    task_description: str | None,
    model: str,
    callback_url: str,
    api_key: str,
    template_definition: dict,
) -> None:
    if pipeline_key in _tasks:
        raise ValueError(f"Pipeline {pipeline_key} is already running")

    ctx = {
        "pipeline_key": pipeline_key,
        "repo_path": repo_path,
        "issue_number": issue_number,
        "issue_title": task_description or "",
        "task_description": task_description or "",
        "model": model,
        "callback_url": callback_url,
        "api_key": api_key,
        "cost_usd": 0,
        "template_definition": template_definition,
    }

    logger.info("Pipeline %s: starting template '%s'", pipeline_key, template_definition.get("name", "unnamed"))
    task = asyncio.create_task(_run_pipeline(ctx), name=f"pipeline-{pipeline_key}")
    _tasks[pipeline_key] = task


def cancel(pipeline_key: str) -> bool:
    task = _tasks.get(pipeline_key)
    if task and not task.done():
        task.cancel()
        return True
    return False


def running_keys() -> list[str]:
    return [k for k, t in _tasks.items() if not t.done()]


async def cleanup(pipeline_key: str, repo_path: str, branch: str | None, pr_number: int | None) -> None:
    """Clean up worktree, PR, and branch for a pipeline (called on delete)."""
    # Cancel if still running
    cancelled = cancel(pipeline_key)
    if cancelled:
        # Give the cancel handler a moment to run
        await asyncio.sleep(2)

    slug = re.sub(r"[^a-z0-9]+", "-", pipeline_key.lower()).strip("-")
    worktree_path = str(WORKTREE_DIR / slug)

    # Close PR
    if pr_number and repo_path:
        logger.info("Cleanup %s: closing PR #%d", pipeline_key, pr_number)
        await _run_gh(repo_path, "pr", "close", str(pr_number), "--comment", "Pipeline deleted.")

    # Remove worktree
    if repo_path:
        await _cleanup_worktree(repo_path, worktree_path)

    # Delete remote branch
    if branch and repo_path:
        logger.info("Cleanup %s: deleting branch %s", pipeline_key, branch)
        await _run_git(repo_path, "push", "origin", "--delete", branch)
