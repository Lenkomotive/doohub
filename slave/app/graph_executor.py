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
    max_attempts = 2  # always retry once on error

    # Determine which session to resume (if any)
    resume_from = node.get("resume_from")  # resume another node's session
    resume_self = node.get("resume_self", False)  # resume own session on re-entry
    session_id = None
    if resume_self and f"_session_{node_id}" in ctx:
        session_id = ctx[f"_session_{node_id}"]
    elif resume_from and f"_session_{resume_from}" in ctx:
        session_id = ctx[f"_session_{resume_from}"]
    # else: fresh session (no resume)

    for attempt in range(1, max_attempts + 1):
        if attempt > 1:
            logger.info("Pipeline %s: %s attempt %d/%d", key, node_id, attempt, max_attempts)

        result = await claude_runner.run_prompt(
            prompt=prompt,
            project_path=ctx.get("worktree_path", ctx.get("repo_path", "/projects")),
            model=model,
            timeout=timeout,
            session_key=f"__graph_{key}_{node_id}__",
            claude_session_id=session_id,
        )

        if result.get("type") == "error":
            error_msg = result.get("error", "unknown error")
            if attempt < max_attempts:
                logger.warning("Pipeline %s: %s failed (attempt %d/%d): %s", key, node_id, attempt, max_attempts, error_msg)
                await asyncio.sleep(2 ** attempt)
                continue
            logger.error("Pipeline %s: %s failed after %d attempts: %s", key, node_id, max_attempts, error_msg)
            ctx[f"_error_{node_id}"] = error_msg
            return None

        # Store session per node and track cost
        if result.get("session_id"):
            ctx[f"_session_{node_id}"] = result["session_id"]
        ctx["cost_usd"] = ctx.get("cost_usd", 0) + (result.get("cost_usd") or 0)

        text = result.get("result", "")

        # Auto-detect PR URL in agent output
        if not ctx.get("pr_url"):
            pr_match = re.search(r"https://github\.com/[^\s)]+/pull/(\d+)", text)
            if pr_match:
                ctx["pr_url"] = pr_match.group(0)
                ctx["pr_number"] = int(pr_match.group(1))
                logger.info("Pipeline %s: %s detected PR %s", key, node_id, ctx["pr_url"])

        return text

    return None


async def _handle_condition(node: dict, ctx: dict) -> str | None:
    """Condition node — returns the next node ID based on ctx value."""
    key = ctx["pipeline_key"]
    node_id = node["id"]
    field = node.get("condition_field", "")
    value = ctx.get(field)
    branches = node.get("branches", {})

    # Branches can be a list [{value, target}] or dict {value: target}
    if isinstance(branches, list):
        branch_map = {b["value"]: b["target"] for b in branches if b.get("value") and b.get("target")}
    else:
        branch_map = branches

    # Iteration guard — uses explicit max_iterations_target
    max_iter = node.get("max_iterations")
    counter_field = node.get("iteration_counter", f"_iter_{node_id}")
    if max_iter is not None:
        count = ctx.get(counter_field, 0)
        if count >= max_iter:
            target = node.get("max_iterations_target")
            # Fall back to default_branch for backwards compat
            if not target:
                target = node.get("default_branch")
            logger.warning(
                "Pipeline %s: %s max iterations (%d) reached → %s",
                key, node_id, max_iter, target,
            )
            return target

    next_node = branch_map.get(str(value)) if value is not None else None
    if next_node is None:
        # Fall back to default_branch for backwards compat
        next_node = node.get("default_branch")
    logger.info(
        "Pipeline %s: %s condition %s=%s → %s",
        key, node_id, field, value, next_node,
    )

    # Increment iteration counter
    if max_iter is not None:
        ctx[counter_field] = ctx.get(counter_field, 0) + 1

    return next_node


async def _handle_template(node: dict, ctx: dict, callback) -> str | None:
    """Execute a nested template as a sub-pipeline.

    Looks up the referenced template definition from ctx["_nested_templates"],
    runs it via execute_graph() with a shared context, and merges results back.
    """
    key = ctx["pipeline_key"]
    node_id = node["id"]
    node_name = node.get("name", node_id)
    template_id = str(node.get("template_id", ""))
    nested_templates = ctx.get("_nested_templates", {})

    if not template_id:
        logger.error("Pipeline %s: template node '%s' has no template_id", key, node_id)
        ctx[f"_error_{node_id}"] = "Template node missing template_id"
        return None

    child_definition = nested_templates.get(template_id)
    if not child_definition:
        logger.error("Pipeline %s: nested template '%s' not found for node '%s'", key, template_id, node_id)
        ctx[f"_error_{node_id}"] = f"Nested template {template_id} not found"
        return None

    logger.info(
        "Pipeline %s: entering nested template '%s' (template_id=%s) at node '%s'",
        key, child_definition.get("name", "unnamed"), template_id, node_id,
    )

    # Wrap callback to prefix child step node_ids for uniqueness
    async def child_callback(data: dict) -> None:
        if "step" in data:
            step = data["step"]
            step["node_id"] = f"{node_id}.{step['node_id']}"
            step["node_name"] = f"{node_name} > {step.get('node_name', '')}"
        # Forward step_log with prefix
        if "step_log" in data:
            data["step_log"] = f"[{node_name}] {data['step_log']}"
        # Don't forward terminal status from child — parent controls that
        if data.get("status") in ("done", "failed"):
            child_status = data["status"]
            ctx[f"_child_status_{node_id}"] = child_status
            if child_status == "failed":
                ctx[f"_error_{node_id}"] = data.get("error", "Nested template failed")
            # Report as progress, not terminal
            data["status"] = "running"
        await callback(data)

    # Execute child graph with shared context
    cost_before = ctx.get("cost_usd", 0)
    await execute_graph(child_definition, ctx, child_callback)

    child_status = ctx.pop(f"_child_status_{node_id}", "done")
    if child_status == "failed":
        # Propagate failure
        return None

    return "__template_done__"


_NODE_HANDLERS = {
    "start": _handle_start,
    "end": _handle_end,
    "failed": _handle_failed,
    "claude_agent": _handle_claude_agent,
    "condition": _handle_condition,
    "template": _handle_template,
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
    """Get the first next node (used for failed-retry and legacy fallback)."""
    targets = node.get("targets", [])
    if targets:
        valid = [t for t in targets if t]
        if valid:
            return valid[0]
    if node.get("next"):
        return node["next"]
    edges = edge_map.get(node["id"], [])
    return edges[0] if edges else None


def _get_all_next_nodes(node: dict, edge_map: dict[str, list[str]]) -> list[str]:
    """Get ALL next node IDs for a non-condition node.

    Returns multiple targets when present (for parallel fork).
    """
    targets = node.get("targets", [])
    if targets:
        valid = [t for t in targets if t]
        if valid:
            return valid
    if node.get("next"):
        return [node["next"]]
    return edge_map.get(node["id"], [])


def _find_join_point(
    fork_targets: list[str],
    edge_map: dict[str, list[str]],
) -> str | None:
    """Find the nearest node reachable from ALL fork targets (convergence point).

    Uses BFS from each target to build reachable sets, then returns the first
    node in the intersection (excluding fork targets themselves).
    Returns None if paths don't converge.
    """
    if len(fork_targets) < 2:
        return None

    def _bfs_order(start: str) -> list[str]:
        order: list[str] = []
        seen = {start}
        queue = [start]
        while queue:
            nid = queue.pop(0)
            order.append(nid)
            for next_id in edge_map.get(nid, []):
                if next_id not in seen:
                    seen.add(next_id)
                    queue.append(next_id)
        return order

    reachable = [set(_bfs_order(t)) for t in fork_targets]
    common = reachable[0].copy()
    for r in reachable[1:]:
        common &= r
    # Don't pick a fork target as the join point
    common -= set(fork_targets)
    if not common:
        return None
    # Nearest common node = first in BFS from first target
    for nid in _bfs_order(fork_targets[0]):
        if nid in common:
            return nid
    return None


# ── Segment result codes ──────────────────────────────────────────────────

_SEG_JOIN = "join"        # stopped at join point, ready to continue
_SEG_END = "end"          # reached an end node (pipeline success)
_SEG_FAILED = "failed"    # reached a failed/error node
_SEG_ERROR = "error"      # internal error
_SEG_NO_NEXT = "no_next"  # fell off the graph


# ── Recursive segment executor ────────────────────────────────────────────


async def _execute_segment(
    start_id: str,
    node_map: dict[str, dict],
    edge_map: dict[str, list[str]],
    ctx: dict,
    callback,
    state: dict,
    stop_before: str | None = None,
) -> str:
    """Execute a linear segment of the graph, forking for parallel paths.

    When a non-condition node has multiple outgoing targets, all paths are
    executed concurrently via asyncio.gather. The segment stops BEFORE the
    join point node so the caller can continue from there after all paths
    converge.

    Args:
        start_id: Node to begin execution at.
        stop_before: If set, stop before executing this node (join point).

    Returns:
        A _SEG_* status code indicating how the segment ended.
    """
    key = ctx["pipeline_key"]
    current_id: str | None = start_id

    while current_id is not None:
        # Stop before the join point — the parent continues from here
        if current_id == stop_before:
            return _SEG_JOIN

        node = node_map.get(current_id)
        if node is None:
            logger.error("Pipeline %s: node '%s' not found in template", key, current_id)
            await callback({"pipeline_key": key, "status": "failed", "error": f"Node '{current_id}' not found"})
            return _SEG_ERROR

        node_type = node["type"]
        node_name = node.get("name", current_id)
        handler = _NODE_HANDLERS.get(node_type)

        if handler is None:
            logger.error("Pipeline %s: unknown node type '%s' for node '%s'", key, node_type, current_id)
            await callback({"pipeline_key": key, "status": "failed", "error": f"Unknown node type '{node_type}'"})
            return _SEG_ERROR

        state["visited_count"] += 1
        visited_count = state["visited_count"]
        total_nodes = state["total_nodes"]
        pipeline_start = state["pipeline_start"]

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
            return _SEG_END

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
            return _SEG_FAILED

        # ── Execute node ────────────────────────────────────────────────
        status_label = node.get("status_label")
        node_start = time.monotonic()
        started_at_iso = datetime.now(timezone.utc).isoformat()

        await callback({
            "pipeline_key": key,
            "status": status_label or "running",
            "step_log": f"[{visited_count}/{total_nodes}] Starting: {node_name}",
            "step": _make_step(node, "running", started_at_iso=started_at_iso),
        })
        logger.info("Pipeline %s: %s (%s) → started", key, current_id, node_type)

        if node_type == "template":
            result = await handler(node, ctx, callback)
        else:
            result = await handler(node, ctx)
        node_duration = time.monotonic() - node_start
        logger.info("Pipeline %s: %s completed in %.1fs", key, current_id, node_duration)

        # ── Handle result based on node type ────────────────────────────
        if node_type == "template":
            if result is None:
                tpl_error = ctx.get(f"_error_{current_id}", "Nested template failed")
                logger.error("Pipeline %s: %s template failed: %s", key, current_id, tpl_error)
                await callback({
                    "pipeline_key": key,
                    "status": "failed",
                    "error": f"Template '{node_name}' failed: {tpl_error}",
                    "cost_usd": ctx.get("cost_usd", 0),
                    "step": _make_step(node, "failed", node_start, started_at_iso=started_at_iso, error=tpl_error),
                })
                return _SEG_FAILED

            await callback({
                "pipeline_key": key,
                "status": status_label or "running",
                "cost_usd": ctx.get("cost_usd", 0),
                "step_log": f"[{visited_count}/{total_nodes}] {node_name} completed in {node_duration:.1f}s",
                "step": _make_step(node, "completed", node_start, started_at_iso=started_at_iso),
                **{k: ctx.get(k) for k in ["pr_url", "pr_number", "branch", "claude_session_id", "issue_title"] if ctx.get(k)},
            })
            next_ids = _get_all_next_nodes(node, edge_map)

        elif node_type == "claude_agent":
            if result is None:
                agent_error = ctx.get(f"_error_{current_id}", "Agent returned no result")
                logger.error("Pipeline %s: %s agent failed: %s", key, current_id, agent_error)
                await callback({
                    "pipeline_key": key,
                    "status": "failed",
                    "error": f"Agent '{node_name}' failed: {agent_error}",
                    "cost_usd": ctx.get("cost_usd", 0),
                    "step": _make_step(node, "failed", node_start, started_at_iso=started_at_iso, error=agent_error),
                })
                return _SEG_FAILED

            ctx[f"_raw_{current_id}"] = result

            outputs = node.get("outputs", [])
            if isinstance(outputs, list) and outputs:
                extracted = extract_outputs_from_text(result, outputs)
                for field, value in extracted.items():
                    if value is not None:
                        ctx[field] = value
                        logger.info("Pipeline %s: %s extracted %s=%s", key, current_id, field, value[:100] if len(value) > 100 else value)
                    else:
                        logger.warning("Pipeline %s: %s failed to extract '%s'", key, current_id, field)

            extract_rules = node.get("extract", {})
            if extract_rules:
                extracted = extract_outputs_legacy(result, extract_rules)
                for field, value in extracted.items():
                    if value is not None:
                        ctx[field] = value

            output_summary = None
            all_outputs = node.get("outputs", [])
            if isinstance(all_outputs, list) and all_outputs:
                parts = [f"{o['name']}={ctx.get(o['name'], '?')}" for o in all_outputs if o.get("name")]
                if parts:
                    output_summary = ", ".join(parts)

            await callback({
                "pipeline_key": key,
                "status": status_label or "running",
                "cost_usd": ctx.get("cost_usd", 0),
                "step_log": f"[{visited_count}/{total_nodes}] {node_name} completed in {node_duration:.1f}s",
                "step": _make_step(node, "completed", node_start, started_at_iso=started_at_iso, output=output_summary),
                **{k: ctx.get(k) for k in ["pr_url", "pr_number", "branch", "claude_session_id", "issue_title"] if ctx.get(k)},
            })
            next_ids = _get_all_next_nodes(node, edge_map)

        elif node_type == "condition":
            if result is None:
                logger.error("Pipeline %s: condition '%s' resolved to no target", key, current_id)
                await callback({
                    "pipeline_key": key,
                    "status": "failed",
                    "error": f"Condition '{node_name}' has no valid branch",
                    "cost_usd": ctx.get("cost_usd", 0),
                })
                return _SEG_FAILED

            field = node.get("condition_field", "")
            value = ctx.get(field)
            await callback({
                "pipeline_key": key,
                "status": status_label or "running",
                "step_log": f"[{visited_count}/{total_nodes}] {node_name}: {field}={value} → {result}",
                "step": _make_step(node, "completed", node_start, started_at_iso=started_at_iso, output=f"{field}={value} → {result}"),
            })
            current_id = result
            continue  # Condition always follows exactly one branch

        elif node_type == "start":
            await callback({
                "pipeline_key": key,
                "status": status_label or "running",
                "step": _make_step(node, "completed", node_start, started_at_iso=started_at_iso),
            })
            next_ids = _get_all_next_nodes(node, edge_map)

        else:
            next_ids = _get_all_next_nodes(node, edge_map)

        # ── Follow to next node(s) ─────────────────────────────────────
        if not next_ids:
            return _SEG_NO_NEXT
        elif len(next_ids) == 1:
            current_id = next_ids[0]
        else:
            # ── Parallel fork ──────────────────────────────────────────
            join_point = _find_join_point(next_ids, edge_map)
            path_names = [node_map.get(nid, {}).get("name", nid) for nid in next_ids]
            logger.info(
                "Pipeline %s: %s forking to %d parallel paths [%s] (join: %s)",
                key, current_id, len(next_ids),
                ", ".join(str(n) for n in path_names),
                join_point or "none",
            )
            await callback({
                "pipeline_key": key,
                "status": status_label or "running",
                "step_log": f"Forking: {node_name} → {len(next_ids)} parallel paths",
            })

            tasks = [
                _execute_segment(
                    nid, node_map, edge_map, ctx, callback, state,
                    stop_before=join_point,
                )
                for nid in next_ids
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Check for errors/failures in any path
            for i, r in enumerate(results):
                if isinstance(r, Exception):
                    logger.error("Pipeline %s: parallel path %s crashed: %s", key, next_ids[i], r)
                    await callback({
                        "pipeline_key": key,
                        "status": "failed",
                        "error": f"Parallel path '{path_names[i]}' crashed: {r}",
                        "cost_usd": ctx.get("cost_usd", 0),
                    })
                    return _SEG_ERROR
                if r in (_SEG_FAILED, _SEG_ERROR):
                    return r

            logger.info(
                "Pipeline %s: all %d parallel paths completed, joining at %s",
                key, len(next_ids), join_point or "end",
            )

            if join_point:
                join_name = node_map.get(join_point, {}).get("name", join_point)
                await callback({
                    "pipeline_key": key,
                    "status": status_label or "running",
                    "step_log": f"Parallel paths joined → continuing from {join_name}",
                })
                current_id = join_point
            else:
                # No convergence — check if any path ended successfully
                if any(r == _SEG_END for r in results):
                    return _SEG_END
                return _SEG_NO_NEXT

    return _SEG_NO_NEXT


# ── Top-level graph executor ──────────────────────────────────────────────


async def execute_graph(
    definition: dict,
    ctx: dict,
    callback,
) -> None:
    """Execute a pipeline template graph.

    Supports parallel execution: when a non-condition node has multiple
    outgoing targets, all paths run concurrently via asyncio.gather.
    Paths converge at the nearest common downstream node (join point).

    Note: parallel paths share the same ctx dict. Use different output
    variable names in parallel agent nodes to avoid overwrites.
    """
    key = ctx["pipeline_key"]
    node_map = _build_node_map(definition)
    edge_map = _build_edge_map(definition)

    start_nodes = [n for n in definition.get("nodes", []) if n["type"] == "start"]
    if not start_nodes:
        logger.error("Pipeline %s: no start node found in template", key)
        await callback({"pipeline_key": key, "status": "failed", "error": "No start node in template"})
        return

    state = {
        "visited_count": 0,
        "total_nodes": len(node_map),
        "pipeline_start": time.monotonic(),
    }

    logger.info("Pipeline %s: starting graph execution (%d nodes)", key, state["total_nodes"])
    await callback({
        "pipeline_key": key,
        "status": "starting",
        "step_log": f"Pipeline starting ({state['total_nodes']} nodes in template)",
    })

    result = await _execute_segment(
        start_nodes[0]["id"], node_map, edge_map, ctx, callback, state,
    )

    if result == _SEG_NO_NEXT:
        total_time = time.monotonic() - state["pipeline_start"]
        logger.warning("Pipeline %s: graph ended without reaching an end node (%.1fs)", key, total_time)
        await callback({
            "pipeline_key": key,
            "status": "failed",
            "error": "Pipeline ended without reaching an end node",
            "cost_usd": ctx.get("cost_usd", 0),
        })
