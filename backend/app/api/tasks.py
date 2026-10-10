import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.migration_support import ChecklistItem
from app.models.schemas import (
    ChecklistItemCreate,
    ChecklistItemOut,
    ChecklistItemUpdate,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)
from app.models.task import Task, TaskStatus
from app.services.execution_log import fail_execution, finish_execution, start_execution
from app.services.idempotency import (
    ACTION_ID_HEADER,
    commit_reserved_execution,
    replay_entity,
    reserve_execution,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


async def _require_task(db: AsyncSession, task_id: str, user: dict) -> Task:
    task = await db.get(Task, task_id)
    if not task or task.deleted_at is not None or (task.user_sub is not None and task.user_sub != user["sub"]):
        raise HTTPException(404, "Task not found")
    return task


async def _require_checklist_item(
    db: AsyncSession,
    task_id: str,
    item_id: str,
) -> ChecklistItem:
    item = await db.get(ChecklistItem, item_id)
    if item is None or item.task_id != task_id:
        raise HTTPException(404, "Checklist item not found")
    return item


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Task).where(Task.deleted_at.is_(None), (Task.user_sub.is_(None)) | (Task.user_sub == user["sub"])).order_by(Task.created_at.desc())
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


@router.get("/{task_id}/checklist", response_model=list[ChecklistItemOut])
async def list_checklist_items(
    task_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_task(db, task_id, user)
    result = await db.execute(
        select(ChecklistItem)
        .where(ChecklistItem.task_id == task_id)
        .order_by(
            ChecklistItem.sort_order.asc(),
            ChecklistItem.created_at.asc(),
            ChecklistItem.id.asc(),
        )
    )
    return result.scalars().all()


@router.post("/{task_id}/checklist", response_model=ChecklistItemOut, status_code=201)
async def create_checklist_item(
    task_id: str,
    body: ChecklistItemCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    action_id: str | None = Header(default=None, alias=ACTION_ID_HEADER),
):
    await _require_task(db, task_id, user)
    request_payload = {"task_id": task_id, **body.model_dump(mode="json")}
    reservation = await reserve_execution(
        db,
        user_sub=user["sub"],
        action_type="checklist_item.create",
        action_id=action_id,
        request_payload=request_payload,
        provider="life_assistant",
        entity_type="checklist_item",
        summary="Create checklist item",
    )
    if reservation.is_replay:
        item = await replay_entity(db, reservation, ChecklistItem)
        if item.task_id != task_id:
            raise HTTPException(409, "Previous idempotent Checklist result belongs to another Task")
        return item

    sort_order = body.sort_order
    if sort_order is None:
        result = await db.execute(
            select(func.coalesce(func.max(ChecklistItem.sort_order), -1) + 1).where(
                ChecklistItem.task_id == task_id
            )
        )
        sort_order = int(result.scalar_one())

    item = ChecklistItem(
        id=str(uuid.uuid4()),
        task_id=task_id,
        title=body.title,
        is_done=False,
        sort_order=sort_order,
        created_at=datetime.now(timezone.utc),
    )
    db.add(item)
    await commit_reserved_execution(
        db,
        reservation,
        result="created",
        entity_type="checklist_item",
        entity_id=item.id,
        summary="Checklist item created",
        failure_summary="Create checklist item failed",
        refresh_entity=item,
    )
    return item


@router.patch("/{task_id}/checklist/{item_id}", response_model=ChecklistItemOut)
async def update_checklist_item(
    task_id: str,
    item_id: str,
    body: ChecklistItemUpdate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_task(db, task_id, user)
    item = await _require_checklist_item(db, task_id, item_id)
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="checklist_item.update",
        provider="life_assistant",
        entity_type="checklist_item",
        entity_id=item_id,
        summary="Update checklist item",
    )
    try:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await db.commit()
        await db.refresh(item)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Update checklist item failed")
        raise
    await finish_execution(
        db,
        execution,
        result="updated",
        summary="Checklist item updated",
    )
    return item


@router.delete("/{task_id}/checklist/{item_id}", status_code=204)
async def delete_checklist_item(
    task_id: str,
    item_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await _require_task(db, task_id, user)
    item = await _require_checklist_item(db, task_id, item_id)
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="checklist_item.delete",
        provider="life_assistant",
        entity_type="checklist_item",
        entity_id=item_id,
        summary="Delete checklist item",
    )
    try:
        await db.delete(item)
        await db.commit()
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Delete checklist item failed")
        raise
    await finish_execution(
        db,
        execution,
        result="deleted",
        summary="Checklist item deleted",
    )


@router.get("/{task_id}", response_model=TaskOut)
async def get_task(
    task_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _require_task(db, task_id, user)


@router.patch("/{task_id}", response_model=TaskOut)
async def update_task(
    task_id: str,
    body: TaskUpdate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    task = await _require_task(db, task_id, user)
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
    task = await _require_task(db, task_id, user)
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
    task = await _require_task(db, task_id, user)
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
        await db.execute(delete(ChecklistItem).where(ChecklistItem.task_id == task_id))
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
