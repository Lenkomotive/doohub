import logging
import re
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models.pipeline import Pipeline
from app.models.pipeline_template import PipelineTemplate
from app.models.user import User
from app.schemas.pipeline_template import (
    DryRunNodeReport,
    DryRunRequest,
    DryRunResponse,
    PipelineTemplateCreate,
    PipelineTemplateResponse,
    PipelineTemplateUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pipeline-templates"])


@router.get("/pipeline-templates", response_model=list[PipelineTemplateResponse])
def list_templates(
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return db.query(PipelineTemplate).order_by(PipelineTemplate.created_at.desc()).all()


@router.get("/pipeline-templates/{template_id}", response_model=PipelineTemplateResponse)
def get_template(
    template_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = db.query(PipelineTemplate).filter(PipelineTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


@router.post("/pipeline-templates", status_code=201, response_model=PipelineTemplateResponse)
def create_template(
    body: PipelineTemplateCreate,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    existing = db.query(PipelineTemplate).filter(PipelineTemplate.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Template with this name already exists")

    template = PipelineTemplate(name=body.name, description=body.description, definition=body.definition)
    db.add(template)
    db.commit()
    db.refresh(template)
    logger.info("Created pipeline template '%s' (id=%d)", template.name, template.id)
    return template


@router.put("/pipeline-templates/{template_id}", response_model=PipelineTemplateResponse)
def update_template(
    template_id: int,
    body: PipelineTemplateUpdate,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = db.query(PipelineTemplate).filter(PipelineTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    if body.name is not None:
        dup = db.query(PipelineTemplate).filter(
            PipelineTemplate.name == body.name, PipelineTemplate.id != template_id
        ).first()
        if dup:
            raise HTTPException(status_code=409, detail="Template with this name already exists")
        template.name = body.name

    if body.description is not None:
        template.description = body.description

    if body.definition is not None:
        template.definition = body.definition

    db.commit()
    db.refresh(template)
    logger.info("Updated pipeline template '%s' (id=%d)", template.name, template.id)
    return template


@router.delete("/pipeline-templates/{template_id}", status_code=204)
def delete_template(
    template_id: int,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = db.query(PipelineTemplate).filter(PipelineTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    in_use = db.query(Pipeline).filter(Pipeline.template_id == template_id).first()
    if in_use:
        raise HTTPException(
            status_code=409,
            detail="Cannot delete template: it is referenced by existing pipelines",
        )

    db.delete(template)
    db.commit()
    logger.info("Deleted pipeline template '%s' (id=%d)", template.name, template.id)


# ── Dry-run helpers ──────────────────────────────────────────────────────────


def _find_variables(template: str) -> list[str]:
    return [m.strip() for m in re.findall(r"\{\{(.+?)\}\}", template)]


def _resolve_template(template: str, ctx: dict[str, Any]) -> str:
    def _replace(match: re.Match) -> str:
        key = match.group(1).strip()
        value = ctx.get(key)
        return str(value) if value is not None else ""

    return re.sub(r"\{\{(.+?)\}\}", _replace, template)


def _get_next_nodes(node: dict, edge_map: dict[str, list[str]]) -> list[str]:
    """Resolve next nodes using the same priority as graph_executor._get_next_node."""
    targets = [t for t in node.get("targets", []) if t]
    if targets:
        return targets
    if node.get("next"):
        return [node["next"]]
    return edge_map.get(node["id"], [])


def _dry_run(
    definition: dict, context: dict[str, Any],
) -> tuple[list[DryRunNodeReport], list[str], list[str], bool]:
    node_map: dict[str, dict] = {n["id"]: n for n in definition.get("nodes", [])}
    edge_map: dict[str, list[str]] = {}
    for edge in definition.get("edges", []):
        edge_map.setdefault(edge["from"], []).append(edge["to"])

    # Track which nodes have incoming references
    incoming: set[str] = set()
    for targets in edge_map.values():
        incoming.update(targets)

    reports: list[DryRunNodeReport] = []
    warnings: list[str] = []
    valid = True

    # Check for start node
    start_nodes = [n for n in definition.get("nodes", []) if n["type"] == "start"]
    if not start_nodes:
        warnings.append("No start node found")
        valid = False

    for node in definition.get("nodes", []):
        node_id = node["id"]
        node_type = node["type"]
        node_name = node.get("name", node_id)

        report = DryRunNodeReport(
            node_id=node_id,
            node_name=node_name,
            node_type=node_type,
        )

        if node_type == "claude_agent":
            prompt_template = node.get("prompt_template", "")
            variables = _find_variables(prompt_template)
            missing = [v for v in variables if v not in context]
            report.resolved_prompt = _resolve_template(prompt_template, context)
            report.missing_variables = missing
            if missing:
                warnings.append(f"Node '{node_name}' ({node_id}): missing variables: {', '.join(missing)}")
            report.next_nodes = _get_next_nodes(node, edge_map)

        elif node_type == "condition":
            branches_raw = node.get("branches", {})
            if isinstance(branches_raw, list):
                branch_map = {b["value"]: b["target"] for b in branches_raw if b.get("value") and b.get("target")}
            else:
                branch_map = dict(branches_raw)
            default = node.get("default_branch")
            report.branches = branch_map
            report.default_branch = default

            # Collect all branch targets as next_nodes
            all_targets = list(branch_map.values())
            if default and default not in all_targets:
                all_targets.append(default)
            report.next_nodes = all_targets

            # Add branch targets to incoming set
            incoming.update(all_targets)

            # Validate branch targets exist
            for label, target in branch_map.items():
                if target not in node_map:
                    warnings.append(f"Condition '{node_name}' ({node_id}): branch '{label}' targets unknown node '{target}'")
                    valid = False
            if default and default not in node_map:
                warnings.append(f"Condition '{node_name}' ({node_id}): default_branch targets unknown node '{default}'")
                valid = False

        else:
            report.next_nodes = _get_next_nodes(node, edge_map)

        # Validate next_nodes targets exist (for non-condition nodes)
        if node_type != "condition":
            for target in report.next_nodes:
                if target not in node_map:
                    warnings.append(f"Node '{node_name}' ({node_id}): targets unknown node '{target}'")
                    valid = False

        reports.append(report)

    # Check for unreachable nodes (no incoming edges and not start)
    for node in definition.get("nodes", []):
        if node["type"] != "start" and node["id"] not in incoming:
            warnings.append(f"Node '{node.get('name', node['id'])}' ({node['id']}): unreachable (no incoming edges)")

    # Check for dead-end non-terminal nodes
    terminal_types = {"end", "failed"}
    for report in reports:
        if report.node_type not in terminal_types and not report.next_nodes:
            warnings.append(f"Node '{report.node_name}' ({report.node_id}): dead end (no outgoing edges)")

    # Build execution order: linear walk from start
    execution_order: list[str] = []
    if start_nodes:
        visited: set[str] = set()
        current_id: str | None = start_nodes[0]["id"]
        while current_id and current_id not in visited:
            visited.add(current_id)
            execution_order.append(current_id)
            node = node_map.get(current_id)
            if not node or node["type"] in terminal_types:
                break
            if node["type"] == "condition":
                break  # Can't follow branches without runtime values
            next_nodes = _get_next_nodes(node, edge_map)
            current_id = next_nodes[0] if next_nodes else None

    return reports, warnings, execution_order, valid


@router.post(
    "/pipeline-templates/{template_id}/dry-run",
    response_model=DryRunResponse,
)
def dry_run_template(
    template_id: int,
    body: DryRunRequest,
    db: DBSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    template = db.query(PipelineTemplate).filter(PipelineTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    reports, warnings, execution_order, valid = _dry_run(template.definition, body.context)
    return DryRunResponse(
        template_name=template.name,
        execution_order=execution_order,
        nodes=reports,
        warnings=warnings,
        valid=valid,
    )
