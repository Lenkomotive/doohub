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


def _build_cmd(
    prompt: str,
    model: str,
    claude_session_id: str | None,
    output_format: str,
    interactive: bool,
) -> list[str]:
    cmd = [
        "claude",
        "-p", prompt,
        "--output-format", output_format,
        "--model", model,
        "--dangerously-skip-permissions",
    ]
    if interactive:
        cmd.extend([
            "--append-system-prompt",
            "\n\n## Interactive mode\n"
            "You are in interactive mode. Keep responses concise — this is a phone chat.\n"
            "Before implementing anything, briefly explain your plan and confirm with the user.\n",
        ])
    if claude_session_id:
        cmd.extend(["--resume", claude_session_id])
    return cmd


async def run_prompt(
    prompt: str,
    project_path: str,
    model: str = "claude-opus-4-6",
    claude_session_id: str | None = None,
    timeout: int = 300,
    session_key: str | None = None,
    interactive: bool = False,
) -> dict:
    """Blocking Claude run. Returns parsed result dict."""
    cmd = _build_cmd(prompt, model, claude_session_id, "json", interactive)
    _sync_claude_md()
    _ensure_claude_config()
    await _git_pull(project_path)
    logger.info("Running claude in %s", project_path)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=project_path,
    )
    if session_key:
        _running_procs[session_key] = proc

    try:
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        return {"type": "error", "subtype": "timeout", "error": "Response timed out.", "session_id": claude_session_id}
    finally:
        if session_key:
            _running_procs.pop(session_key, None)
        _ensure_claude_config()

    if proc.returncode != 0:
        err = stderr.decode("utf-8", errors="replace").strip()
        logger.error("Claude exited %d: %s", proc.returncode, err)
        return {"type": "error", "error": err or f"Claude exited with code {proc.returncode}", "session_id": claude_session_id}

    raw = stdout.decode("utf-8", errors="replace").strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"type": "result", "result": raw, "session_id": claude_session_id}


async def stream_prompt(
    prompt: str,
    project_path: str,
    model: str = "claude-opus-4-6",
    claude_session_id: str | None = None,
    timeout: int = 300,
    session_key: str | None = None,
    interactive: bool = False,
):
    """Streaming Claude run. Yields event dicts:
    - {"event": "token", "session_key": key, "token": "..."}
    - {"event": "done",  "session_key": key, "result": "...", "session_id": "...", "cost_usd": ...}
    - {"event": "error", "session_key": key, "error": "..."}
    """
    cmd = _build_cmd(prompt, model, claude_session_id, "stream-json", interactive)
    _sync_claude_md()
    _ensure_claude_config()
    await _git_pull(project_path)
    logger.info("Streaming claude in %s", project_path)

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=project_path,
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
                    if block.get("type") == "text":
                        chunk = block["text"]
                        result_text += chunk
                        yield {"event": "token", "session_key": key, "token": chunk}
            elif etype == "result":
                new_session_id = event.get("session_id", new_session_id)
                cost_usd = event.get("cost_usd")
                result_text = event.get("result", result_text)

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
