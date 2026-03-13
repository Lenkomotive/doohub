import asyncio
import json
import logging
from pathlib import Path

from app.config import settings
from app.roles import build_mode_prompt

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


def _build_cmd(
    prompt: str,
    model: str,
    claude_session_id: str | None,
    mode: str = "general",
    project_path: str = ".",
) -> list[str]:
    cmd = [
        "claude",
        "-p", prompt,
        "--output-format", "json",
        "--model", model,
        "--dangerously-skip-permissions",
    ]

    system_prompt = build_mode_prompt(mode, project_path)
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
    mode: str = "general",
) -> dict:
    """Blocking Claude run. Returns parsed result dict."""
    cmd = _build_cmd(prompt, model, claude_session_id, mode, project_path)
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
