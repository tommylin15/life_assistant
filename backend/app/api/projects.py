import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.drive import ProjectDriveDocument
from app.models.note import Note
from app.models.project import Project
from app.models.schemas import ProjectCreate, ProjectOut, ProjectUpdate
from app.models.shopping import ShoppingList
from app.models.task import Task
from app.services.execution_log import fail_execution, finish_execution, start_execution
from app.services.idempotency import (
    ACTION_ID_HEADER,
    commit_reserved_execution,
    replay_entity,
    reserve_execution,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
async def list_projects(_user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    action_id: str | None = Header(default=None, alias=ACTION_ID_HEADER),
):
    reservation = await reserve_execution(
        db,
        user_sub=user["sub"],
        action_type="project.create",
        action_id=action_id,
        request_payload=body.model_dump(mode="json"),
        provider="internal",
        entity_type="project",
        summary="Create project",
    )
    if reservation.is_replay:
        return await replay_entity(db, reservation, Project)

    project = Project(id=str(uuid.uuid4()), **body.model_dump())
    db.add(project)
    await commit_reserved_execution(
        db,
        reservation,
        result="created",
        entity_type="project",
        entity_id=project.id,
        summary="Project created",
        failure_summary="Project create failed",
        refresh_entity=project,
    )
    return project


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(project_id: str, _user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(project_id: str, body: ProjectUpdate, user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    execution = await start_execution(db, user_sub=user["sub"], action_type="project.update", provider="internal", entity_type="project", entity_id=project_id, summary="Update project")
    try:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        await db.commit()
        await db.refresh(project)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Project update failed")
        raise
    await finish_execution(db, execution, result="updated", summary="Project updated")
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(project_id: str, user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    linked_task_result = await db.execute(
        select(Task.id).where(Task.project_id == project_id, Task.deleted_at.is_(None)).limit(1)
    )
    if linked_task_result.scalar_one_or_none() is not None:
        raise HTTPException(409, "Project has linked tasks")

    linked_note_result = await db.execute(select(Note.id).where(Note.project_id == project_id).limit(1))
    if linked_note_result.scalar_one_or_none() is not None:
        raise HTTPException(409, "Project has linked notes")

    linked_shopping_result = await db.execute(select(ShoppingList.id).where(ShoppingList.project_id == project_id).limit(1))
    if linked_shopping_result.scalar_one_or_none() is not None:
        raise HTTPException(409, "Project has linked shopping lists")

    linked_drive_result = await db.execute(
        select(ProjectDriveDocument.drive_document_id)
        .where(ProjectDriveDocument.project_id == project_id)
        .limit(1)
    )
    if linked_drive_result.scalar_one_or_none() is not None:
        raise HTTPException(409, "Project has linked Drive documents")

    execution = await start_execution(db, user_sub=user["sub"], action_type="project.delete", provider="internal", entity_type="project", entity_id=project_id, summary="Delete project")
    try:
        await db.delete(project)
        await db.commit()
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Project delete failed")
        raise
    await finish_execution(db, execution, result="deleted", summary="Project deleted")
