import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.core.auth import get_current_user, require_slave_api_key
from app.core.database import get_db
from app.models.pipeline import Pipeline
from app.models.pipeline_template import PipelineTemplate
from app.models.user import User
from app.schemas.pipeline_template import (
    PipelineTemplateCreate,
    PipelineTemplateResponse,
    PipelineTemplateUpdate,
)

logger = logging.getLogger(__name__)
router = APIRouter(tags=["pipeline-templates"])


def _check_circular_refs(
    db: DBSession, definition: dict, current_id: int, visited: set[int] | None = None
) -> None:
    """Recursively check that template node references don't form cycles."""
    if visited is None:
        visited = {current_id}
    for node in definition.get("nodes", []):
        if node.get("type") != "template":
            continue
        ref_id = node.get("template_id")
        if not ref_id:
            continue
        ref_id = int(ref_id)
        if ref_id in visited:
            raise ValueError(
                f"Circular template reference detected: template {ref_id} "
                f"is already in the reference chain"
            )
        ref = db.query(PipelineTemplate).filter(PipelineTemplate.id == ref_id).first()
        if not ref:
            raise ValueError(f"Node '{node['id']}' references template {ref_id} which does not exist")
        visited.add(ref_id)
        _check_circular_refs(db, ref.definition, current_id, visited)
        visited.discard(ref_id)


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
        _check_circular_refs(db, body.definition, template_id)
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

    # Check if any other template references this one as a nested template node
    all_templates = db.query(PipelineTemplate).filter(PipelineTemplate.id != template_id).all()
    for t in all_templates:
        for node in (t.definition or {}).get("nodes", []):
            if node.get("type") == "template" and int(node.get("template_id", 0)) == template_id:
                raise HTTPException(
                    status_code=409,
                    detail=f"Cannot delete template: it is referenced as a node in template '{t.name}'",
                )

    db.delete(template)
    db.commit()
    logger.info("Deleted pipeline template '%s' (id=%d)", template.name, template.id)


# --- internal endpoints (slave -> backend) ---


@router.get("/internal/pipeline-templates")
def internal_list_templates(
    db: DBSession = Depends(get_db),
    _auth: None = Depends(require_slave_api_key),
):
    templates = db.query(PipelineTemplate).order_by(PipelineTemplate.created_at.desc()).all()
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "definition": t.definition,
            "created_at": t.created_at.isoformat(),
            "updated_at": t.updated_at.isoformat(),
        }
        for t in templates
    ]


@router.get("/internal/pipeline-templates/{template_id}")
def internal_get_template(
    template_id: int,
    db: DBSession = Depends(get_db),
    _auth: None = Depends(require_slave_api_key),
):
    template = db.query(PipelineTemplate).filter(PipelineTemplate.id == template_id).first()
    if not template:
        raise HTTPException(status_code=404, detail="Template not found")
    return {
        "id": template.id,
        "name": template.name,
        "description": template.description,
        "definition": template.definition,
        "created_at": template.created_at.isoformat(),
        "updated_at": template.updated_at.isoformat(),
    }


@router.post("/internal/pipeline-templates", status_code=201)
def internal_create_template(
    body: PipelineTemplateCreate,
    db: DBSession = Depends(get_db),
    _auth: None = Depends(require_slave_api_key),
):
    existing = db.query(PipelineTemplate).filter(PipelineTemplate.name == body.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Template with this name already exists")
    template = PipelineTemplate(name=body.name, description=body.description, definition=body.definition)
    db.add(template)
    db.commit()
    db.refresh(template)
    logger.info("Internal: created template '%s' (id=%d)", template.name, template.id)
    return {"id": template.id, "name": template.name}


@router.put("/internal/pipeline-templates/{template_id}")
def internal_update_template(
    template_id: int,
    body: PipelineTemplateUpdate,
    db: DBSession = Depends(get_db),
    _auth: None = Depends(require_slave_api_key),
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
        _check_circular_refs(db, body.definition, template_id)
        template.definition = body.definition
    db.commit()
    db.refresh(template)
    logger.info("Internal: updated template '%s' (id=%d)", template.name, template.id)
    return {"id": template.id, "name": template.name}
