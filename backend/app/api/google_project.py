import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.api.google_integrations import (
    CAPABILITIES,
    _get_gmail_metadata,
    _gmail_source_note,
)
from app.db.session import get_db
from app.models.project import Project
from app.services.execution_log import fail_execution, finish_execution, start_execution
from app.services.google_oauth import SERVICE_SCOPES

router = APIRouter(prefix="/integrations/google", tags=["google-integrations"])

GMAIL_TO_PROJECT_CAPABILITY = {
    "name": "gmail.to_project",
    "version": "1.0",
    "service": "gmail",
    "required_scope": SERVICE_SCOPES["gmail"][0],
    "required_scopes": [SERVICE_SCOPES["gmail"][0]],
    "risk": "write_internal",
    "confirmation": "explicit_user_or_policy",
}

if not any(
    item.get("name") == GMAIL_TO_PROJECT_CAPABILITY["name"]
    for item in CAPABILITIES
):
    CAPABILITIES.append(GMAIL_TO_PROJECT_CAPABILITY)


class GmailToProjectCreate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=500)
    summary: str | None = Field(default=None, max_length=10000)
    status: str = Field(default="active", min_length=1, max_length=32)


@router.post("/gmail/messages/{message_id}/project", status_code=201)
async def gmail_message_to_project(
    message_id: str,
    body: GmailToProjectCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="gmail.to_project",
        provider="google",
        entity_type="gmail_message",
        entity_id=message_id,
        summary="Convert Gmail message to project",
    )
    try:
        message = await _get_gmail_metadata(db, user["sub"], message_id)
        source_note = _gmail_source_note(message)
        summary = (
            source_note
            if not body.summary
            else f"{body.summary}\n\n{source_note}"
        )
        name = (
            body.name
            or str(message.get("subject") or "").strip()
            or "Gmail project"
        )[:500]
        project = Project(
            id=str(uuid.uuid4()),
            name=name,
            summary=summary,
            status=body.status,
        )
        db.add(project)
        await db.commit()
        await db.refresh(project)
    except Exception as exc:
        await fail_execution(
            db,
            execution,
            exc,
            summary="Gmail to project conversion failed",
        )
        raise

    await finish_execution(
        db,
        execution,
        result="created",
        entity_type="project",
        entity_id=project.id,
        summary="Gmail message converted to project",
    )
    return {
        "project": {
            "id": project.id,
            "name": project.name,
            "summary": project.summary,
            "status": project.status,
            "created_at": project.created_at,
            "updated_at": project.updated_at,
        },
        "source": {
            "gmail_message_id": message.get("id"),
            "thread_id": message.get("thread_id"),
        },
    }
