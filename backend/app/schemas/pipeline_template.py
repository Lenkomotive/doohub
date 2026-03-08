from collections import defaultdict, deque
from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

ALLOWED_NODE_TYPES = {"start", "end", "failed", "claude_agent", "condition"}
TERMINAL_NODE_TYPES = {"end", "failed"}


def _get_branch_targets(node: dict) -> list[str]:
    """Extract target node IDs from a condition node's branches."""
    branches = node.get("branches")
    if not branches:
        return []
    if isinstance(branches, dict):
        return [t for t in branches.values() if t]
    if isinstance(branches, list):
        return [b["target"] for b in branches if isinstance(b, dict) and b.get("target")]
    return []


def _build_adjacency(nodes: list[dict], edges: list[dict]) -> dict[str, set[str]]:
    """Build adjacency map covering all outgoing paths per node."""
    adj: dict[str, set[str]] = defaultdict(set)

    # Edges
    for edge in edges:
        adj[edge["from"]].add(edge["to"])

    node_map = {n["id"]: n for n in nodes}
    for nid, node in node_map.items():
        # targets (filter empty strings, like the executor does)
        for t in node.get("targets", []):
            if t:
                adj[nid].add(t)

        # next (legacy)
        if node.get("next"):
            adj[nid].add(node["next"])

        # condition-specific
        if node.get("type") == "condition":
            for t in _get_branch_targets(node):
                adj[nid].add(t)
            if node.get("default_branch"):
                adj[nid].add(node["default_branch"])
            if node.get("max_iterations_target"):
                adj[nid].add(node["max_iterations_target"])

    return adj


def _validate_definition(definition: dict[str, Any]) -> dict[str, Any]:
    required_keys = {"version", "name", "nodes", "edges"}
    missing = required_keys - definition.keys()
    if missing:
        raise ValueError(f"Definition missing required keys: {', '.join(sorted(missing))}")

    nodes = definition["nodes"]
    if not isinstance(nodes, list) or len(nodes) == 0:
        raise ValueError("Definition 'nodes' must be a non-empty list")

    node_ids = set()
    for i, node in enumerate(nodes):
        if not isinstance(node, dict):
            raise ValueError(f"Node at index {i} must be an object")
        if "id" not in node:
            raise ValueError(f"Node at index {i} missing 'id'")
        if "type" not in node:
            raise ValueError(f"Node at index {i} missing 'type'")
        if node["type"] not in ALLOWED_NODE_TYPES:
            raise ValueError(
                f"Node '{node['id']}' has invalid type '{node['type']}'. "
                f"Allowed: {', '.join(sorted(ALLOWED_NODE_TYPES))}"
            )
        if node["id"] in node_ids:
            raise ValueError(f"Duplicate node ID: '{node['id']}'")
        node_ids.add(node["id"])

    edges = definition["edges"]
    if not isinstance(edges, list):
        raise ValueError("Definition 'edges' must be a list")

    for i, edge in enumerate(edges):
        if not isinstance(edge, dict):
            raise ValueError(f"Edge at index {i} must be an object")
        if "from" not in edge:
            raise ValueError(f"Edge at index {i} missing 'from'")
        if "to" not in edge:
            raise ValueError(f"Edge at index {i} missing 'to'")
        if edge["from"] not in node_ids:
            raise ValueError(f"Edge at index {i}: 'from' references unknown node '{edge['from']}'")
        if edge["to"] not in node_ids:
            raise ValueError(f"Edge at index {i}: 'to' references unknown node '{edge['to']}'")

    # --- Structural checks ---

    node_map = {n["id"]: n for n in nodes}

    # Exactly one start node
    start_nodes = [n for n in nodes if n["type"] == "start"]
    if len(start_nodes) != 1:
        raise ValueError(f"Expected exactly 1 start node, found {len(start_nodes)}")

    # At least one terminal node
    terminal_nodes = [n for n in nodes if n["type"] in TERMINAL_NODE_TYPES]
    if len(terminal_nodes) == 0:
        raise ValueError("Definition must have at least one 'end' or 'failed' node")

    # Node-specific required fields
    for node in nodes:
        nid = node["id"]
        ntype = node["type"]
        if ntype == "claude_agent":
            if not node.get("prompt_template"):
                raise ValueError(f"Node '{nid}': claude_agent must have a non-empty 'prompt_template'")
        elif ntype == "condition":
            if not node.get("condition_field"):
                raise ValueError(f"Node '{nid}': condition must have a non-empty 'condition_field'")
            if not node.get("branches"):
                raise ValueError(f"Node '{nid}': condition must have non-empty 'branches'")

    # --- Connectivity / reference checks ---

    for node in nodes:
        nid = node["id"]
        # targets
        for t in node.get("targets", []):
            if t and t not in node_ids:
                raise ValueError(f"Node '{nid}': targets references unknown node '{t}'")
        # next
        if node.get("next") and node["next"] not in node_ids:
            raise ValueError(f"Node '{nid}': next references unknown node '{node['next']}'")
        # condition-specific references
        if node.get("type") == "condition":
            for t in _get_branch_targets(node):
                if t not in node_ids:
                    raise ValueError(f"Node '{nid}': branch references unknown node '{t}'")
            if node.get("default_branch") and node["default_branch"] not in node_ids:
                raise ValueError(
                    f"Node '{nid}': default_branch references unknown node '{node['default_branch']}'"
                )
            if node.get("max_iterations_target") and node["max_iterations_target"] not in node_ids:
                raise ValueError(
                    f"Node '{nid}': max_iterations_target references unknown node "
                    f"'{node['max_iterations_target']}'"
                )

    # --- Reachability (BFS from start) ---

    adj = _build_adjacency(nodes, edges)
    start_id = start_nodes[0]["id"]
    visited: set[str] = set()
    queue = deque([start_id])
    visited.add(start_id)
    while queue:
        current = queue.popleft()
        for neighbor in adj[current]:
            if neighbor not in visited:
                visited.add(neighbor)
                queue.append(neighbor)

    unreachable = node_ids - visited
    if unreachable:
        raise ValueError(f"Nodes not reachable from start: {', '.join(sorted(unreachable))}")

    # --- Dead-end check ---

    dead_ends = [
        nid for nid in node_ids
        if node_map[nid]["type"] not in TERMINAL_NODE_TYPES and not adj[nid]
    ]
    if dead_ends:
        raise ValueError(
            f"Non-terminal nodes with no outgoing edges (dead ends): {', '.join(sorted(dead_ends))}"
        )

    # --- Cycle safety ---
    # Every cycle must pass through a condition node with max_iterations set.

    def _find_unguarded_cycle() -> list[str] | None:
        """DFS to find a cycle not guarded by a condition with max_iterations."""
        WHITE, GRAY, BLACK = 0, 1, 2
        color = {nid: WHITE for nid in node_ids}
        parent: dict[str, str | None] = {}

        def _dfs(u: str, path: list[str]) -> list[str] | None:
            color[u] = GRAY
            path.append(u)
            for v in adj[u]:
                if color[v] == GRAY:
                    # Found a cycle: extract it
                    cycle_start = path.index(v)
                    cycle = path[cycle_start:]
                    # Check if any node in the cycle is a condition with max_iterations
                    has_guard = any(
                        node_map[n]["type"] == "condition" and node_map[n].get("max_iterations")
                        for n in cycle
                    )
                    if not has_guard:
                        return cycle
                elif color[v] == WHITE:
                    result = _dfs(v, path)
                    if result is not None:
                        return result
            path.pop()
            color[u] = BLACK
            return None

        for nid in node_ids:
            if color[nid] == WHITE:
                result = _dfs(nid, [])
                if result is not None:
                    return result
        return None

    unguarded_cycle = _find_unguarded_cycle()
    if unguarded_cycle:
        cycle_str = " -> ".join(unguarded_cycle + [unguarded_cycle[0]])
        raise ValueError(
            f"Cycle detected without max_iterations guard: {cycle_str}"
        )

    return definition


class PipelineTemplateCreate(BaseModel):
    name: str
    description: str | None = None
    definition: dict[str, Any]

    @field_validator("definition")
    @classmethod
    def validate_definition(cls, v: dict[str, Any]) -> dict[str, Any]:
        return _validate_definition(v)


class PipelineTemplateUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    definition: dict[str, Any] | None = None

    @field_validator("definition")
    @classmethod
    def validate_definition(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        if v is not None:
            return _validate_definition(v)
        return v


class PipelineTemplateResponse(BaseModel):
    id: int
    name: str
    description: str | None = None
    definition: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
