"""Pipeline orchestrator — plan → develop → review state machine.

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

from app import claude_runner
from app.agent_prompts import developer_prompt, planner_prompt, reviewer_prompt
from app.config import settings
from app.graph_executor import execute_graph

logger = logging.getLogger(__name__)

WORKTREE_DIR = settings.data_dir / "worktrees"
MAX_REVIEW_ROUNDS = 3

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


def _extract_pr_url(text: str) -> str | None:
    match = re.search(r"https://github\.com/[^\s)]+/pull/\d+", text)
    return match.group(0) if match else None


def _extract_pr_number(url: str) -> int | None:
    match = re.search(r"/pull/(\d+)", url)
    return int(match.group(1)) if match else None


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


# ── Agent Runners ────────────────────────────────────────────────────────────


async def _run_planner(ctx: dict, worktree_path: str) -> str | None:
    prompt = planner_prompt(
        ctx.get("issue_number"),
        ctx.get("issue_title", ""),
        ctx.get("issue_body", ""),
    )
    result = await claude_runner.run_prompt(
        prompt=prompt,
        project_path=worktree_path,
        model=ctx["model"],
        timeout=600,
        session_key=f"__orch_plan_{ctx['pipeline_key']}__",
    )
    if result.get("type") == "error":
        logger.error("Planner failed: %s", result.get("error"))
        return None
    return result.get("result", "")


async def _run_developer(ctx: dict, worktree_path: str, review_comments: str | None = None) -> str | None:
    branch = ctx["branch"]
    is_retry = ctx.get("review_round", 0) > 0

    if is_retry:
        await _run_git(worktree_path, "fetch", "origin")
        await _run_git(worktree_path, "rebase", "origin/main")

    prompt = developer_prompt(
        ctx.get("issue_number"),
        ctx.get("issue_title", ""),
        ctx.get("issue_body", ""),
        ctx.get("plan", "No plan available."),
        branch,
        review_comments,
    )
    result = await claude_runner.run_prompt(
        prompt=prompt,
        project_path=worktree_path,
        model=ctx["model"],
        timeout=900,
        session_key=f"__orch_dev_{ctx['pipeline_key']}__",
        claude_session_id=ctx.get("claude_session_id") if is_retry else None,
    )
    if result.get("type") == "error":
        logger.error("Developer failed: %s", result.get("error"))
        return None

    ctx["claude_session_id"] = result.get("session_id")
    ctx["cost_usd"] = ctx.get("cost_usd", 0) + (result.get("cost_usd") or 0)
    return _extract_pr_url(result.get("result", ""))


async def _run_reviewer(ctx: dict, worktree_path: str) -> str | None:
    prompt = reviewer_prompt(
        ctx.get("issue_number"),
        ctx.get("issue_title", ""),
        ctx["pr_number"],
    )
    result = await claude_runner.run_prompt(
        prompt=prompt,
        project_path=worktree_path,
        model=ctx["model"],
        timeout=600,
        session_key=f"__orch_review_{ctx['pipeline_key']}__",
    )
    if result.get("type") == "error":
        logger.error("Reviewer failed: %s", result.get("error"))
        return None

    ctx["cost_usd"] = ctx.get("cost_usd", 0) + (result.get("cost_usd") or 0)
    text = result.get("result", "").upper()
    if "APPROVED" in text and "CHANGES_REQUESTED" not in text:
        return "APPROVED"
    if "CHANGES_REQUESTED" in text:
        return "CHANGES_REQUESTED"
    logger.warning("Could not parse reviewer verdict: %s", text[:200])
    return None


# ── Pipeline State Machine ───────────────────────────────────────────────────


async def _run_graph_pipeline(ctx: dict) -> None:
    """Execute a pipeline using the graph executor with a template definition."""
    key = ctx["pipeline_key"]
    cb_url = ctx["callback_url"]
    api_key = ctx["api_key"]
    repo_path = ctx["repo_path"]
    definition = ctx["template_definition"]

    logger.info("Pipeline %s: using graph executor (template: %s)", key, definition.get("name", "unnamed"))

    # Fetch issue details if needed
    if ctx.get("issue_number") and not ctx.get("issue_body"):
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

        # Run the graph
        async def cb(data: dict) -> None:
            await _callback(cb_url, api_key, data)

        await execute_graph(definition, ctx, cb)

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


async def _run_pipeline(ctx: dict) -> None:
    """Execute the full plan → develop → review pipeline (legacy path)."""
    key = ctx["pipeline_key"]
    cb_url = ctx["callback_url"]
    api_key = ctx["api_key"]
    repo_path = ctx["repo_path"]

    # Fetch issue details if we have an issue number but no body
    if ctx.get("issue_number") and not ctx.get("issue_body"):
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
        # 1. Plan
        await _callback(cb_url, api_key, {
            "pipeline_key": key, "status": "planning", "step_log": "Starting planner agent",
        })
        worktree_path = await _ensure_worktree(repo_path, key, ctx["branch"])
        if not worktree_path:
            await _callback(cb_url, api_key, {
                "pipeline_key": key, "status": "failed", "error": "Failed to create worktree",
            })
            return

        plan = await _run_planner(ctx, worktree_path)
        if not plan:
            await _callback(cb_url, api_key, {
                "pipeline_key": key, "status": "failed", "error": "Planner agent failed",
            })
            return

        ctx["plan"] = plan

        # Post plan as issue comment
        if ctx.get("issue_number"):
            await _run_gh(
                worktree_path, "issue", "comment",
                str(ctx["issue_number"]),
                "--body", f"## Implementation Plan\n\n{plan}",
            )

        await _callback(cb_url, api_key, {
            "pipeline_key": key, "status": "planned", "plan": plan,
            "step_log": "Plan complete, starting developer",
        })

        # 2. Develop
        await _callback(cb_url, api_key, {
            "pipeline_key": key, "status": "developing",
        })
        pr_url = await _run_developer(ctx, worktree_path)
        if not pr_url:
            await _callback(cb_url, api_key, {
                "pipeline_key": key, "status": "failed", "error": "Developer agent failed",
            })
            return

        pr_number = _extract_pr_number(pr_url)
        ctx["pr_number"] = pr_number
        await _callback(cb_url, api_key, {
            "pipeline_key": key, "status": "developed",
            "pr_url": pr_url, "pr_number": pr_number,
            "branch": ctx["branch"],
            "claude_session_id": ctx.get("claude_session_id"),
            "cost_usd": ctx.get("cost_usd", 0),
            "step_log": f"PR opened: {pr_url}",
        })

        # 3. Review loop
        for round_num in range(MAX_REVIEW_ROUNDS):
            ctx["review_round"] = round_num
            await _callback(cb_url, api_key, {
                "pipeline_key": key, "status": "reviewing",
                "step_log": f"Review round {round_num + 1}",
            })

            verdict = await _run_reviewer(ctx, worktree_path)
            if not verdict:
                await _callback(cb_url, api_key, {
                    "pipeline_key": key, "status": "failed", "error": "Reviewer agent failed",
                })
                return

            if verdict == "APPROVED":
                await _callback(cb_url, api_key, {
                    "pipeline_key": key, "status": "done",
                    "cost_usd": ctx.get("cost_usd", 0),
                    "step_log": "Review approved — PR ready to merge",
                })
                await _cleanup_worktree(repo_path, worktree_path)
                return

            # Changes requested — re-develop
            review_comments = None
            if pr_number:
                code, out = await _run_gh(
                    worktree_path, "pr", "view", str(pr_number),
                    "--json", "reviews",
                    "-q", '[.reviews[] | select(.state == "CHANGES_REQUESTED") | .body] | last',
                )
                if code == 0 and out:
                    review_comments = out

            await _callback(cb_url, api_key, {
                "pipeline_key": key, "status": "developing",
                "step_log": f"Changes requested (round {round_num + 1}/{MAX_REVIEW_ROUNDS})",
            })

            pr_url = await _run_developer(ctx, worktree_path, review_comments)
            if not pr_url:
                await _callback(cb_url, api_key, {
                    "pipeline_key": key, "status": "failed",
                    "error": f"Developer failed on review round {round_num + 1}",
                })
                return

            await _callback(cb_url, api_key, {
                "pipeline_key": key, "status": "developed",
                "cost_usd": ctx.get("cost_usd", 0),
                "step_log": f"Fixes pushed for round {round_num + 1}",
            })

        # Exhausted review rounds
        await _callback(cb_url, api_key, {
            "pipeline_key": key, "status": "failed",
            "error": f"Max review rounds ({MAX_REVIEW_ROUNDS}) reached",
            "cost_usd": ctx.get("cost_usd", 0),
        })

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
    template_definition: dict | None = None,
) -> None:
    if pipeline_key in _tasks:
        raise ValueError(f"Pipeline {pipeline_key} is already running")

    ctx = {
        "pipeline_key": pipeline_key,
        "repo_path": repo_path,
        "issue_number": issue_number,
        "issue_title": task_description or "",
        "issue_body": task_description or "",
        "model": model,
        "callback_url": callback_url,
        "api_key": api_key,
        "cost_usd": 0,
    }

    if template_definition:
        ctx["template_definition"] = template_definition
        logger.info("Pipeline %s: starting with template '%s'", pipeline_key, template_definition.get("name", "unnamed"))
        runner = _run_graph_pipeline(ctx)
    else:
        logger.info("Pipeline %s: starting with legacy orchestrator", pipeline_key)
        runner = _run_pipeline(ctx)

    task = asyncio.create_task(runner, name=f"pipeline-{pipeline_key}")
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
