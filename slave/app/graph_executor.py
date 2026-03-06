"""Generic graph executor for pipeline templates.

Reads a JSON pipeline definition and executes nodes in order,
following edges and condition branches. Reports progress via callbacks.
"""
import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any

from app import claude_runner

logger = logging.getLogger(__name__)


# ── Template variable resolution ────────────────────────────────────────────


def resolve_template(template: str, ctx: dict[str, Any]) -> str:
    """Replace {{var}} placeholders in a template string with values from ctx."""
    def _replace(match: re.Match) -> str:
        key = match.group(1).strip()
        value = ctx.get(key)
        if value is None:
            logger.debug("Pipeline %s: template var {{%s}} not found in ctx", ctx.get("pipeline_key", "?"), key)
            return ""
        return str(value)

    return re.sub(r"\{\{(.+?)\}\}", _replace, template)


# ── Output extraction ──────────────────────────────────────────────────────


def extract_outputs_from_text(text: str, outputs: list[dict]) -> dict[str, str | None]:
    """Extract named outputs from agent response text.

    Outputs format (from builder):
        [{"name": "field_name", "values": ["yes", "no"]}]

    If values is non-empty, searches for one of the allowed values (keyword match).
    If values is empty, stores the full text as the output value.
    """
    results: dict[str, str | None] = {}
    upper_text = text.upper()

    for output in outputs:
        name = output.get("name", "")
        if not name:
            continue
        values = output.get("values", [])

        if values:
            # Keyword match: find which value appears in the text
            found = None
            for v in values:
                if v.strip().upper() in upper_text:
                    found = v.strip()
                    break
            results[name] = found
        else:
            # No constrained values: store full text
            results[name] = text

    return results


def extract_outputs_legacy(text: str, extract_rules: dict[str, str]) -> dict[str, str | None]:
    """Legacy extract rules format: {"field": "regex:<pattern>"} or {"field": "keyword:A|B|C"}."""
    results: dict[str, str | None] = {}

    for field, rule in extract_rules.items():
        if rule.startswith("regex:"):
            pattern = rule[len("regex:"):]
            match = re.search(pattern, text)
            results[field] = match.group(0) if match else None
        elif rule.startswith("keyword:"):
            keywords = rule[len("keyword:"):].split("|")
            upper_text = text.upper()
            found = None
            for kw in keywords:
                if kw.strip().upper() in upper_text:
                    found = kw.strip()
                    break
            results[field] = found
        else:
            logger.warning("Unknown extract rule for field '%s': %s", field, rule)
            results[field] = None

    return results


# ── Node handlers ───────────────────────────────────────────────────────────


async def _handle_start(node: dict, ctx: dict) -> str | None:
    """Start node — just passes through to the next edge."""
    return None


async def _handle_end(node: dict, ctx: dict) -> str | None:
    """End node — terminal success. Resolves result_template if present."""
    result_template = node.get("result_template", "")
    if result_template:
        ctx["_end_result"] = resolve_template(result_template, ctx)
    return None


async def _handle_failed(node: dict, ctx: dict) -> str | None:
    """Failed node — terminal failure. Resolves reason_template if present."""
    reason_template = node.get("reason_template", "")
    if reason_template:
        ctx["_fail_reason"] = resolve_template(reason_template, ctx)
    return None


async def _handle_claude_agent(node: dict, ctx: dict) -> str | None:
    """Run a Claude agent node. Returns the raw result text."""
    key = ctx["pipeline_key"]
    node_id = node["id"]
    prompt_template = node.get("prompt_template", "")
    prompt = resolve_template(prompt_template, ctx)
    model = node.get("model") or ctx.get("model", "claude-sonnet-4-6")
    timeout = node.get("timeout", 600)
    retry_config = node.get("retry", {})
    max_attempts = retry_config.get("max_attempts", 1)

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            logger.info("Pipeline %s: %s attempt %d/%d", key, node_id, attempt, max_attempts)

        result = await claude_runner.run_prompt(
            prompt=prompt,
            project_path=ctx.get("worktree_path", ctx.get("repo_path", "/projects")),
            model=model,
            timeout=timeout,
            session_key=f"__graph_{key}_{node_id}__",
            claude_session_id=ctx.get("claude_session_id"),
        )

        if result.get("type") == "error":
            error_msg = result.get("error", "unknown error")
            if attempt < max_attempts:
                logger.warning("Pipeline %s: %s failed (attempt %d/%d): %s", key, node_id, attempt, max_attempts, error_msg)
                await asyncio.sleep(2 ** attempt)
                continue
            logger.error("Pipeline %s: %s failed after %d attempts: %s", key, node_id, max_attempts, error_msg)
            return None

        # Track session and cost
        if result.get("session_id"):
            ctx["claude_session_id"] = result["session_id"]
        ctx["cost_usd"] = ctx.get("cost_usd", 0) + (result.get("cost_usd") or 0)

        return result.get("result", "")

    return None


async def _handle_condition(node: dict, ctx: dict) -> str | None:
    """Condition node — returns the next node ID based on ctx value."""
    key = ctx["pipeline_key"]
    node_id = node["id"]
    field = node.get("condition_field", "")
    value = ctx.get(field)
    branches = node.get("branches", {})
    default = node.get("default_branch")

    # Branches can be a list [{value, target}] or dict {value: target}
    if isinstance(branches, list):
        branch_map = {b["value"]: b["target"] for b in branches if b.get("value") and b.get("target")}
    else:
        branch_map = branches

    # Iteration guard
    max_iter = node.get("max_iterations")
    counter_field = node.get("iteration_counter", f"_iter_{node_id}")
    if max_iter is not None:
        count = ctx.get(counter_field, 0)
        if count >= max_iter:
            logger.warning(
                "Pipeline %s: %s max iterations (%d) reached → %s",
                key, node_id, max_iter, default,
            )
            return default

    next_node = branch_map.get(str(value), default) if value is not None else default
    logger.info(
        "Pipeline %s: %s condition %s=%s → %s",
        key, node_id, field, value, next_node,
    )

    # Increment iteration counter
    if max_iter is not None:
        ctx[counter_field] = ctx.get(counter_field, 0) + 1

    return next_node


_NODE_HANDLERS = {
    "start": _handle_start,
    "end": _handle_end,
    "failed": _handle_failed,
    "claude_agent": _handle_claude_agent,
    "condition": _handle_condition,
}


# ── Step log helpers ─────────────────────────────────────────────────────────


def _make_step(node: dict, status: str, started_at: float | None = None, **extra) -> dict:
    """Build a step log dict for callback reporting."""
    now = time.monotonic()
    step = {
        "node_id": node["id"],
        "node_name": node.get("name", node["id"]),
        "node_type": node["type"],
        "status": status,
        "started_at": extra.pop("started_at_iso", None) or datetime.now(timezone.utc).isoformat(),
    }
    if status in ("completed", "failed", "skipped"):
        step["completed_at"] = datetime.now(timezone.utc).isoformat()
        if started_at is not None:
            step["duration_s"] = round(now - started_at, 1)
    for k, v in extra.items():
        if v is not None:
            step[k] = v
    return step


# ── Graph execution ─────────────────────────────────────────────────────────


def _build_edge_map(definition: dict) -> dict[str, list[str]]:
    """Build a map of node_id → [next_node_ids] from edges."""
    edge_map: dict[str, list[str]] = {}
    for edge in definition.get("edges", []):
        edge_map.setdefault(edge["from"], []).append(edge["to"])
    return edge_map


def _build_node_map(definition: dict) -> dict[str, dict]:
    """Build a map of node_id → node definition."""
    return {node["id"]: node for node in definition.get("nodes", [])}


def _get_next_node(node: dict, edge_map: dict[str, list[str]]) -> str | None:
    """Get the next node for a non-condition node.

    Uses the node's 'targets' field if present (from builder),
    otherwise falls back to edge_map. Returns first target.
    """
    targets = node.get("targets", [])
    if targets:
        # Filter empty strings
        valid = [t for t in targets if t]
        if valid:
            return valid[0]

    # Legacy: 'next' field
    if node.get("next"):
        return node["next"]

    # Fallback to edge map
    edges = edge_map.get(node["id"], [])
    return edges[0] if edges else None


async def execute_graph(
    definition: dict,
    ctx: dict,
    callback,
) -> None:
    """Execute a pipeline template graph.

    Args:
        definition: The JSON pipeline template definition.
        ctx: Shared context dict (pipeline_key, repo_path, worktree_path, etc.).
        callback: Async function(data: dict) to report status updates.
    """
    key = ctx["pipeline_key"]
    node_map = _build_node_map(definition)
    edge_map = _build_edge_map(definition)

    # Find start node
    start_nodes = [n for n in definition.get("nodes", []) if n["type"] == "start"]
    if not start_nodes:
        logger.error("Pipeline %s: no start node found in template", key)
        await callback({"pipeline_key": key, "status": "failed", "error": "No start node in template"})
        return

    current_id = start_nodes[0]["id"]
    pipeline_start = time.monotonic()
    total_nodes = len(node_map)
    visited_count = 0
    logger.info("Pipeline %s: starting graph execution (%d nodes)", key, total_nodes)

    # Initial callback: pipeline is starting
    await callback({
        "pipeline_key": key,
        "status": "starting",
        "step_log": f"Pipeline starting ({total_nodes} nodes in template)",
    })

    while current_id is not None:
        node = node_map.get(current_id)
        if node is None:
            logger.error("Pipeline %s: node '%s' not found in template", key, current_id)
            await callback({"pipeline_key": key, "status": "failed", "error": f"Node '{current_id}' not found"})
            return

        node_type = node["type"]
        node_name = node.get("name", current_id)
        handler = _NODE_HANDLERS.get(node_type)

        if handler is None:
            logger.error("Pipeline %s: unknown node type '%s' for node '%s'", key, node_type, current_id)
            await callback({"pipeline_key": key, "status": "failed", "error": f"Unknown node type '{node_type}'"})
            return

        visited_count += 1

        # ── End node (success) ─────────────────────────────────────────
        if node_type == "end":
            await handler(node, ctx)
            total_time = time.monotonic() - pipeline_start
            result_msg = ctx.get("_end_result", "")
            logger.info(
                "Pipeline %s: reached end node '%s' (%s) in %.1fs",
                key, current_id, node_name, total_time,
            )
            await callback({
                "pipeline_key": key,
                "status": "done",
                "cost_usd": ctx.get("cost_usd", 0),
                "step_log": f"Pipeline done: {node_name}" + (f" — {result_msg}" if result_msg else ""),
                "step": _make_step(node, "completed", pipeline_start, output=result_msg or None),
            })
            return

        # ── Failed node (terminal failure) ─────────────────────────────
        if node_type == "failed":
            await handler(node, ctx)
            total_time = time.monotonic() - pipeline_start
            reason = ctx.get("_fail_reason", "")
            logger.info(
                "Pipeline %s: reached failed node '%s' (%s) in %.1fs",
                key, current_id, node_name, total_time,
            )
            fail_step = _make_step(node, "failed", pipeline_start, error=reason or None)
            # Failed nodes can have targets (retry flow)
            next_id = _get_next_node(node, edge_map)
            if next_id:
                logger.info("Pipeline %s: failed node '%s' has next → %s", key, current_id, next_id)
                await callback({
                    "pipeline_key": key,
                    "status": node.get("status_label", "failed"),
                    "cost_usd": ctx.get("cost_usd", 0),
                    "step_log": f"Failed: {node_name}" + (f" — {reason}" if reason else "") + f", continuing to {next_id}",
                    "step": fail_step,
                })
                current_id = next_id
                continue
            # Terminal failure
            await callback({
                "pipeline_key": key,
                "status": "failed",
                "error": reason or f"Pipeline failed at: {node_name}",
                "cost_usd": ctx.get("cost_usd", 0),
                "step_log": f"Pipeline failed: {node_name}" + (f" — {reason}" if reason else ""),
                "step": fail_step,
            })
            return

        # ── Execute node ────────────────────────────────────────────────
        status_label = node.get("status_label")

        node_start = time.monotonic()
        started_at_iso = datetime.now(timezone.utc).isoformat()

        # Always send a "entering node" callback
        await callback({
            "pipeline_key": key,
            "status": status_label or "running",
            "step_log": f"[{visited_count}/{total_nodes}] Starting: {node_name}",
            "step": _make_step(node, "running", started_at_iso=started_at_iso),
        })
        logger.info("Pipeline %s: %s (%s) → started", key, current_id, node_type)

        result = await handler(node, ctx)
        node_duration = time.monotonic() - node_start
        logger.info("Pipeline %s: %s completed in %.1fs", key, current_id, node_duration)

        # ── Handle result based on node type ────────────────────────────
        if node_type == "claude_agent":
            if result is None:
                # Agent failed
                logger.error("Pipeline %s: %s agent returned no result", key, current_id)
                await callback({
                    "pipeline_key": key,
                    "status": "failed",
                    "error": f"Agent '{node_name}' failed",
                    "cost_usd": ctx.get("cost_usd", 0),
                    "step": _make_step(node, "failed", node_start, started_at_iso=started_at_iso, error="Agent returned no result"),
                })
                return

            # Store raw result in ctx under node_id
            ctx[f"_raw_{current_id}"] = result

            # Extract outputs (new format: [{name, values}])
            outputs = node.get("outputs", [])
            if isinstance(outputs, list) and outputs:
                extracted = extract_outputs_from_text(result, outputs)
                for field, value in extracted.items():
                    if value is not None:
                        ctx[field] = value
                        logger.info("Pipeline %s: %s extracted %s=%s", key, current_id, field, value[:100] if len(value) > 100 else value)
                    else:
                        logger.warning("Pipeline %s: %s failed to extract '%s'", key, current_id, field)

            # Legacy extract rules
            extract_rules = node.get("extract", {})
            if extract_rules:
                extracted = extract_outputs_legacy(result, extract_rules)
                for field, value in extracted.items():
                    if value is not None:
                        ctx[field] = value

            # Build output summary for step log
            output_summary = None
            all_outputs = node.get("outputs", [])
            if isinstance(all_outputs, list) and all_outputs:
                parts = [f"{o['name']}={ctx.get(o['name'], '?')}" for o in all_outputs if o.get("name")]
                if parts:
                    output_summary = ", ".join(parts)

            # Report progress
            await callback({
                "pipeline_key": key,
                "status": status_label or "running",
                "cost_usd": ctx.get("cost_usd", 0),
                "step_log": f"[{visited_count}/{total_nodes}] {node_name} completed in {node_duration:.1f}s",
                "step": _make_step(node, "completed", node_start, started_at_iso=started_at_iso, output=output_summary),
                **{k: ctx.get(k) for k in ["pr_url", "pr_number", "branch", "claude_session_id", "issue_title"] if ctx.get(k)},
            })

            # Follow to next node
            current_id = _get_next_node(node, edge_map)

        elif node_type == "condition":
            # result is the next node ID (or None)
            if result is None:
                logger.error("Pipeline %s: condition '%s' resolved to no target", key, current_id)
                await callback({
                    "pipeline_key": key,
                    "status": "failed",
                    "error": f"Condition '{node_name}' has no valid branch",
                    "cost_usd": ctx.get("cost_usd", 0),
                })
                return

            field = node.get("condition_field", "")
            value = ctx.get(field)
            await callback({
                "pipeline_key": key,
                "status": status_label or "running",
                "step_log": f"[{visited_count}/{total_nodes}] {node_name}: {field}={value} → {result}",
                "step": _make_step(node, "completed", node_start, started_at_iso=started_at_iso, output=f"{field}={value} → {result}"),
            })
            current_id = result

        elif node_type == "start":
            await callback({
                "pipeline_key": key,
                "status": status_label or "running",
                "step": _make_step(node, "completed", node_start, started_at_iso=started_at_iso),
            })
            current_id = _get_next_node(node, edge_map)

        else:
            current_id = _get_next_node(node, edge_map)

    # Fell off the graph (no more edges)
    total_time = time.monotonic() - pipeline_start
    logger.warning("Pipeline %s: graph ended without reaching an end node (%.1fs)", key, total_time)
    await callback({
        "pipeline_key": key,
        "status": "failed",
        "error": "Pipeline ended without reaching an end node",
        "cost_usd": ctx.get("cost_usd", 0),
    })
