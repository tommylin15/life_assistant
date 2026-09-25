import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.project import Project
from app.models.schemas import ProjectCreate, ProjectOut, ProjectUpdate
from app.models.task import Task
from app.services.execution_log import fail_execution, finish_execution, start_execution

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
async def list_projects(
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Project).order_by(Project.created_at.desc()))
    return result.scalars().all()


@router.post("", response_model=ProjectOut, status_code=201)
async def create_project(
    body: ProjectCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="project.create",
        provider="internal",
        entity_type="project",
        summary="Create project",
    )
    project = Project(id=str(uuid.uuid4()), **body.model_dump())
    try:
        db.add(project)
        await db.commit()
        await db.refresh(project)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Project create failed")
        raise
    await finish_execution(
        db,
        execution,
        result="created",
        entity_id=project.id,
        summary="Project created",
    )
    return project


@router.get("/{project_id}", response_model=ProjectOut)
async def get_project(
    project_id: str,
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: str,
    body: ProjectUpdate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="project.update",
        provider="internal",
        entity_type="project",
        entity_id=project_id,
        summary="Update project",
    )
    try:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(project, field, value)
        await db.commit()
        await db.refresh(project)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Project update failed")
        raise
    await finish_execution(
        db,
        execution,
        result="updated",
        summary="Project updated",
    )
    return project


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    project = await db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project not found")

    linked_result = await db.execute(
        select(Task.id).where(Task.project_id == project_id).limit(1)
    )
    if linked_result.scalar_one_or_none() is not None:
        raise HTTPException(409, "Project has linked tasks")

    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="project.delete",
        provider="internal",
        entity_type="project",
        entity_id=project_id,
        summary="Delete project",
    )
    try:
        await db.delete(project)
        await db.commit()
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Project delete failed")
        raise
    await finish_execution(
        db,
        execution,
        result="deleted",
        summary="Project deleted",
    )
