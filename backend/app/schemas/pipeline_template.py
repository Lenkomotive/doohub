from datetime import datetime
from typing import Any

from pydantic import BaseModel, field_validator

ALLOWED_NODE_TYPES = {"start", "end", "failed", "claude_agent", "condition", "template"}


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
        if node["type"] == "template":
            if not node.get("template_id"):
                raise ValueError(
                    f"Node '{node['id']}' of type 'template' must have a non-empty 'template_id'"
                )
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
