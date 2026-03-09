import asyncio
import json
import logging
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

_claude_md_dst = Path.home() / ".claude" / "CLAUDE.md"
_claude_json = Path.home() / ".claude.json"
_claude_backup_dir = Path.home() / ".claude" / "backups"

# Running processes keyed by session_key so cancel() can find them.
_running_procs: dict[str, asyncio.subprocess.Process] = {}


def _sync_claude_md() -> None:
    """Copy CLAUDE.md from the mounted source into ~/.claude/CLAUDE.md."""
    src = settings.claude_md_src
    if src.exists():
        _claude_md_dst.parent.mkdir(parents=True, exist_ok=True)
        _claude_md_dst.write_text(src.read_text())


def _ensure_claude_config() -> None:
    """Restore .claude.json from backup if missing or corrupted."""
    if _claude_json.exists():
        try:
            json.loads(_claude_json.read_text())
            return
        except (json.JSONDecodeError, OSError):
            logger.warning(".claude.json corrupted, attempting restore")

    if not _claude_backup_dir.exists():
        return
    backups = sorted(_claude_backup_dir.glob(".claude.json.backup.*"))
    if not backups:
        return
    latest = backups[-1]
    try:
        json.loads(latest.read_text())
        import shutil
        shutil.copy2(latest, _claude_json)
        logger.info("Restored .claude.json from %s", latest.name)
    except (json.JSONDecodeError, OSError) as e:
        logger.error("Failed to restore .claude.json: %s", e)


async def _git_pull(project_path: str) -> None:
    if not (Path(project_path) / ".git").exists():
        return
    try:
        proc = await asyncio.create_subprocess_exec(
            "git", "pull",
            cwd=project_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)
        if proc.returncode != 0:
            logger.warning("git pull failed in %s: %s", project_path, stderr.decode().strip())
        else:
            logger.info("git pull OK in %s", project_path)
    except Exception as e:
        logger.warning("git pull error in %s: %s", project_path, e)


_MODE_PROMPTS: dict[str, str] = {
    "planning": (
        "\n\n## Planning mode\n"
        "You are in planning mode. Your job is to analyze, plan, and outline — NOT implement.\n"
        "- Read and explore the codebase to understand the current state\n"
        "- Provide a clear, structured plan with steps and trade-offs\n"
        "- Do NOT write code, create files, or make changes\n"
        "- Ask clarifying questions when the requirements are ambiguous\n"
        "- Keep responses concise and well-structured\n"
    ),
    "analysis": (
        "\n\n## Analysis mode\n"
        "You are in read-only analysis mode. Explore and explain — do NOT modify anything.\n"
        "- Read files, search code, and analyze the codebase\n"
        "- Provide insights, explain patterns, identify issues\n"
        "- Do NOT write, edit, or create any files\n"
        "- Do NOT run commands that modify state (no git commits, no installs, etc.)\n"
        "- Keep responses concise\n"
    ),
    "freeform": (
        "\n\n## Interactive mode\n"
        "You are in interactive mode. This is a conversational back-and-forth session.\n"
        "- Keep responses concise — this is a live chat\n"
        "- Before implementing anything, briefly explain your plan and ask for confirmation\n"
        "- After making changes, summarize what you did\n"
        "- Ask clarifying questions when needed\n"
    ),
}

_MODE_ALLOWED_TOOLS: dict[str, list[str]] = {
    "analysis": ["Read", "Glob", "Grep", "Bash(git status:*)", "Bash(git log:*)", "Bash(git diff:*)"],
}


def _build_cmd(
    prompt: str,
    model: str,
    claude_session_id: str | None,
    output_format: str,
    mode: str = "oneshot",
) -> list[str]:
    cmd = [
        "claude",
        "-p", prompt,
        "--output-format", output_format,
        "--model", model,
    ]

    allowed_tools = _MODE_ALLOWED_TOOLS.get(mode)
    if allowed_tools:
        cmd.append("--allowedTools")
        cmd.extend(allowed_tools)
    else:
        cmd.append("--dangerously-skip-permissions")

    system_prompt = _MODE_PROMPTS.get(mode)
    if system_prompt:
        cmd.extend(["--append-system-prompt", system_prompt])

    if claude_session_id:
        cmd.extend(["--resume", claude_session_id])
    return cmd


def _resolve_cwd(project_path: str) -> str:
    p = Path(project_path)
    if p.is_dir():
        return str(p)
    logger.warning("project_path %r does not exist, falling back to home", project_path)
    return str(Path.home())


async def run_prompt(
    prompt: str,
    project_path: str,
    model: str = "claude-opus-4-6",
    claude_session_id: str | None = None,
    timeout: int = 300,
    session_key: str | None = None,
    mode: str = "oneshot",
) -> dict:
    """Blocking Claude run. Returns parsed result dict."""
    cmd = _build_cmd(prompt, model, claude_session_id, "json", mode)
    _sync_claude_md()
    _ensure_claude_config()
    await _git_pull(project_path)
    cwd = _resolve_cwd(project_path)
    logger.info("Running claude in %s session=%s model=%s", cwd, session_key, model)

    import time as _time
    _start = _time.monotonic()

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    if session_key:
        _running_procs[session_key] = proc

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        logger.warning("Claude timed out after %ds session=%s", timeout, session_key)
        return {"type": "error", "subtype": "timeout", "error": "Response timed out.", "session_id": claude_session_id}
    finally:
        if session_key:
            _running_procs.pop(session_key, None)
        _ensure_claude_config()

    duration = round(_time.monotonic() - _start, 1)

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace").strip()
        logger.error("Claude exited %d after %.1fs session=%s: %s", proc.returncode, duration, session_key, err)
        return {"type": "error", "error": err or f"Claude exited with code {proc.returncode}", "session_id": claude_session_id}

    logger.info("Claude finished in %.1fs session=%s", duration, session_key)
    raw = stdout.decode("utf-8", errors="replace").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"type": "result", "result": raw.strip(), "session_id": claude_session_id}


async def stream_prompt(
    prompt: str,
    project_path: str,
    model: str = "claude-opus-4-6",
    claude_session_id: str | None = None,
    timeout: int = 300,
    session_key: str | None = None,
    mode: str = "oneshot",
):
    """Streaming Claude run. Yields event dicts:
    - {"event": "token", "session_key": key, "token": "..."}
    - {"event": "tool_use", "session_key": key, "tool": "...", "input": {...}}
    - {"event": "tool_result", "session_key": key, "tool": "...", "output": "..."}
    - {"event": "done",  "session_key": key, "result": "...", "session_id": "...", "cost_usd": ...}
    - {"event": "error", "session_key": key, "error": "..."}
    """
    cmd = _build_cmd(prompt, model, claude_session_id, "stream-json", mode)
    _sync_claude_md()
    _ensure_claude_config()
    await _git_pull(project_path)
    cwd = _resolve_cwd(project_path)
    logger.info("Streaming claude in %s session=%s model=%s", cwd, session_key, model)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    if session_key:
        _running_procs[session_key] = proc

    key = session_key or "unknown"
    result_text = ""
    new_session_id = claude_session_id
    cost_usd = None

    try:
        deadline = asyncio.get_event_loop().time() + timeout
        async for raw_line in proc.stdout:
            if asyncio.get_event_loop().time() > deadline:
                proc.kill()
                await proc.wait()
                yield {"event": "error", "session_key": key, "error": "Response timed out."}
                return

            line = raw_line.decode("utf-8", errors="replace").strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            etype = event.get("type")
            if etype == "assistant":
                for block in event.get("message", {}).get("content", []):
                    btype = block.get("type")
                    if btype == "text":
                        chunk = block["text"]
                        result_text += chunk
                        yield {"event": "token", "session_key": key, "token": chunk}
                    elif btype == "tool_use":
                        yield {
                            "event": "tool_use",
                            "session_key": key,
                            "tool": block.get("name", ""),
                            "input": block.get("input", {}),
                        }
                    elif btype == "tool_result":
                        yield {
                            "event": "tool_result",
                            "session_key": key,
                            "tool": block.get("name", ""),
                            "output": block.get("content", block.get("text", "")),
                        }
            elif etype == "result":
                new_session_id = event.get("session_id", new_session_id)
                cost_usd = event.get("cost_usd")
                result_text = event.get("result", result_text).strip()

        await proc.wait()

    except Exception as e:
        proc.kill()
        await proc.wait()
        yield {"event": "error", "session_key": key, "error": str(e)}
        return
    finally:
        if session_key:
            _running_procs.pop(session_key, None)
        _ensure_claude_config()

    if proc.returncode != 0:
        err = (await proc.stderr.read()).decode("utf-8", errors="replace").strip()
        yield {"event": "error", "session_key": key, "error": err or f"Claude exited with code {proc.returncode}"}
        return

    yield {
        "event": "done",
        "session_key": key,
        "result": result_text,
        "session_id": new_session_id,
        "cost_usd": cost_usd,
    }


async def cancel(session_key: str) -> bool:
    """Kill a running Claude process. Returns True if something was killed."""
    proc = _running_procs.pop(session_key, None)
    if proc and proc.returncode is None:
        proc.kill()
        await proc.wait()
        _ensure_claude_config()
        logger.info("Cancelled process for %s", session_key)
        return True
    return False
