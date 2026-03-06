"""Generic graph executor for pipeline templates.

Reads a JSON pipeline definition and executes nodes in order,
following edges and condition branches. Reports progress via callbacks.
"""
import asyncio
import logging
import re
import time
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


def extract_outputs(text: str, extract_rules: dict[str, str]) -> dict[str, str | None]:
    """Extract named outputs from agent text using regex or keyword rules.

    Rules format:
        {"field": "regex:<pattern>"}    — first match of regex
        {"field": "keyword:A|B|C"}      — first keyword found (case-insensitive)
    """
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
    """End node — terminal, returns the end status."""
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

    next_node = branches.get(str(value), default) if value is not None else default
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
    "claude_agent": _handle_claude_agent,
    "condition": _handle_condition,
}


# ── Graph execution ─────────────────────────────────────────────────────────


def _build_edge_map(definition: dict) -> dict[str, str]:
    """Build a map of node_id → next_node_id from edges."""
    edge_map: dict[str, str] = {}
    for edge in definition.get("edges", []):
        edge_map[edge["from"]] = edge["to"]
    return edge_map


def _build_node_map(definition: dict) -> dict[str, dict]:
    """Build a map of node_id → node definition."""
    return {node["id"]: node for node in definition.get("nodes", [])}


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
    logger.info("Pipeline %s: starting graph execution (%d nodes)", key, len(node_map))

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

        # ── End node ────────────────────────────────────────────────────
        if node_type == "end":
            end_status = node.get("status", "done")
            total_time = time.monotonic() - pipeline_start
            logger.info(
                "Pipeline %s: reached end node '%s' (status=%s) in %.1fs",
                key, current_id, end_status, total_time,
            )
            await callback({
                "pipeline_key": key,
                "status": end_status,
                "cost_usd": ctx.get("cost_usd", 0),
                "step_log": f"Pipeline finished: {end_status}",
            })
            return

        # ── Execute node ────────────────────────────────────────────────
        status_label = node.get("status_label")
        if status_label:
            await callback({
                "pipeline_key": key,
                "status": status_label,
                "step_log": f"Running: {node_name}",
            })

        node_start = time.monotonic()
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
                })
                return

            # Store raw result in ctx under node_id
            ctx[f"_raw_{current_id}"] = result

            # Extract outputs
            extract_rules = node.get("extract", {})
            if extract_rules:
                extracted = extract_outputs(result, extract_rules)
                for field, value in extracted.items():
                    if value is not None:
                        ctx[field] = value
                        logger.info("Pipeline %s: %s extracted %s=%s", key, current_id, field, value)
                    else:
                        logger.warning("Pipeline %s: %s failed to extract '%s'", key, current_id, field)

            # Store named outputs
            for output_name in node.get("outputs", []):
                if output_name not in ctx:
                    # If not already extracted, store the full result
                    ctx[output_name] = result
                    logger.info("Pipeline %s: %s output %s stored (full result)", key, current_id, output_name)

            # Report progress
            await callback({
                "pipeline_key": key,
                "status": status_label or "running",
                "cost_usd": ctx.get("cost_usd", 0),
                "step_log": f"{node_name} completed in {node_duration:.1f}s",
                **{k: ctx.get(k) for k in ["pr_url", "pr_number", "branch", "claude_session_id"] if ctx.get(k)},
            })

            # Follow edge to next node
            current_id = edge_map.get(current_id)

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
            current_id = result

        elif node_type == "start":
            current_id = edge_map.get(current_id)

        else:
            current_id = edge_map.get(current_id)

    # Fell off the graph (no more edges)
    total_time = time.monotonic() - pipeline_start
    logger.warning("Pipeline %s: graph ended without reaching an end node (%.1fs)", key, total_time)
    await callback({
        "pipeline_key": key,
        "status": "failed",
        "error": "Pipeline ended without reaching an end node",
        "cost_usd": ctx.get("cost_usd", 0),
    })
