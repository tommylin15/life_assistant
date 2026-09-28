import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.schemas import TaskCreate, TaskOut, TaskUpdate
from app.models.task import Task, TaskStatus
from app.services.execution_log import fail_execution, finish_execution, start_execution
from app.services.idempotency import (
    ACTION_ID_HEADER,
    commit_reserved_execution,
    replay_entity,
    reserve_execution,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.deleted_at.is_(None)).order_by(Task.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=TaskOut, status_code=201)
async def create_task(
    body: TaskCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    action_id: str | None = Header(default=None, alias=ACTION_ID_HEADER),
):
    reservation = await reserve_execution(
        db,
        user_sub=user["sub"],
        action_type="task.create",
        action_id=action_id,
        request_payload=body.model_dump(mode="json"),
        provider="life_assistant",
        entity_type="task",
        summary="Create task",
    )
    if reservation.is_replay:
        task = await replay_entity(db, reservation, Task)
        if task.deleted_at is not None:
            raise HTTPException(409, "Previous idempotent Task result was deleted")
        return task

    task = Task(id=str(uuid.uuid4()), **body.model_dump())
    db.add(task)
    await commit_reserved_execution(
        db,
        reservation,
        result="created",
        entity_type="task",
        entity_id=task.id,
        summary="Task created",
        failure_summary="Create task failed",
        refresh_entity=task,
    )
    return task


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str,
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(404, "Task not found")
    return task


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: str,
    body: TaskUpdate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(404, "Task not found")
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="task.update",
        provider="life_assistant",
        entity_type="task",
        entity_id=task_id,
        summary="Update task",
    )
    try:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(task, field, value)
        if "status" in body.model_fields_set:
            task.completed_at = (
                datetime.now(timezone.utc)
                if body.status == TaskStatus.completed
                else None
            )
        await db.commit()
        await db.refresh(task)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Update task failed")
        raise
    await finish_execution(
        db,
        execution,
        result="updated",
        summary="Task updated",
    )
    return task


@router.post("/{task_id}/complete", response_model=TaskOut)
async def complete_task(
    task_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(404, "Task not found")
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="task.complete",
        provider="life_assistant",
        entity_type="task",
        entity_id=task_id,
        summary="Complete task",
    )
    try:
        task.status = TaskStatus.completed
        task.completed_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(task)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Complete task failed")
        raise
    await finish_execution(
        db,
        execution,
        result="completed",
        summary="Task completed",
    )
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await db.get(Task, task_id)
    if not task or task.deleted_at is not None:
        raise HTTPException(404, "Task not found")
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="task.delete",
        provider="life_assistant",
        entity_type="task",
        entity_id=task_id,
        summary="Delete task",
    )
    try:
        await db.delete(task)
        await db.commit()
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Delete task failed")
        raise
    await finish_execution(
        db,
        execution,
        result="deleted",
        summary="Task deleted",
    )
