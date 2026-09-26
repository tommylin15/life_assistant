import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.schemas import TemplateCreate, TemplateOut, TemplateUpdate
from app.models.template import Template
from app.services.execution_log import fail_execution, finish_execution, start_execution

router = APIRouter(prefix="/templates", tags=["templates"])


@router.get("", response_model=list[TemplateOut])
async def list_templates(
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Template).order_by(Template.updated_at.desc()))
    return result.scalars().all()


@router.post("", response_model=TemplateOut, status_code=201)
async def create_template(
    body: TemplateCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="template.create",
        provider="life_assistant",
        entity_type="template",
        summary=f"Create template: {body.name}",
    )
    template = Template(id=str(uuid.uuid4()), **body.model_dump())
    try:
        db.add(template)
        await db.commit()
        await db.refresh(template)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Create template failed")
        raise
    await finish_execution(
        db,
        execution,
        result="created",
        entity_id=template.id,
        summary=f"Template created: {template.name}",
    )
    return template


@router.get("/{template_id}", response_model=TemplateOut)
async def get_template(
    template_id: str,
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    template = await db.get(Template, template_id)
    if not template:
        raise HTTPException(404, "Template not found")
    return template


@router.patch("/{template_id}", response_model=TemplateOut)
async def update_template(
    template_id: str,
    body: TemplateUpdate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    template = await db.get(Template, template_id)
    if not template:
        raise HTTPException(404, "Template not found")
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="template.update",
        provider="life_assistant",
        entity_type="template",
        entity_id=template_id,
        summary=f"Update template: {template.name}",
    )
    try:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(template, field, value)
        await db.commit()
        await db.refresh(template)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Update template failed")
        raise
    await finish_execution(
        db,
        execution,
        result="updated",
        summary=f"Template updated: {template.name}",
    )
    return template
