import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DBSession

from app.core.auth import get_current_user
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

    template = PipelineTemplate(name=body.name, definition=body.definition)
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
