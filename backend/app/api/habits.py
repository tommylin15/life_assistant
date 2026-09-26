import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.habit import Habit, HabitCompletion
from app.models.schemas import HabitCompletionOut, HabitCreate, HabitOut, HabitUpdate
from app.services.execution_log import fail_execution, finish_execution, start_execution

router = APIRouter(prefix="/habits", tags=["habits"])


@router.get("", response_model=list[HabitOut])
async def list_habits(
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Habit).where(Habit.is_active.is_(True)).order_by(Habit.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=HabitOut, status_code=201)
async def create_habit(
    body: HabitCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="habit.create",
        provider="life_assistant",
        entity_type="habit",
        summary="Create habit",
    )
    habit = Habit(id=str(uuid.uuid4()), **body.model_dump())
    try:
        db.add(habit)
        await db.commit()
        await db.refresh(habit)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Create habit failed")
        raise
    await finish_execution(
        db,
        execution,
        result="created",
        entity_id=habit.id,
        summary="Habit created",
    )
    return habit


@router.get("/{habit_id}", response_model=HabitOut)
async def get_habit(
    habit_id: str,
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    habit = await db.get(Habit, habit_id)
    if not habit:
        raise HTTPException(404, "Habit not found")
    return habit


@router.patch("/{habit_id}", response_model=HabitOut)
async def update_habit(
    habit_id: str,
    body: HabitUpdate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    habit = await db.get(Habit, habit_id)
    if not habit:
        raise HTTPException(404, "Habit not found")
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="habit.update",
        provider="life_assistant",
        entity_type="habit",
        entity_id=habit_id,
        summary="Update habit",
    )
    try:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(habit, field, value)
        await db.commit()
        await db.refresh(habit)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Update habit failed")
        raise
    await finish_execution(
        db,
        execution,
        result="updated",
        summary="Habit updated",
    )
    return habit


@router.post("/{habit_id}/complete", response_model=HabitCompletionOut, status_code=201)
async def complete_habit(
    habit_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    habit = await db.get(Habit, habit_id)
    if not habit:
        raise HTTPException(404, "Habit not found")
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="habit.complete",
        provider="life_assistant",
        entity_type="habit",
        entity_id=habit_id,
        summary="Complete habit",
    )
    completion = HabitCompletion(id=str(uuid.uuid4()), habit_id=habit_id)
    try:
        db.add(completion)
        await db.commit()
        await db.refresh(completion)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Complete habit failed")
        raise
    await finish_execution(
        db,
        execution,
        result="completed",
        summary="Habit completed",
    )
    return completion


@router.get("/{habit_id}/completions", response_model=list[HabitCompletionOut])
async def list_habit_completions(
    habit_id: str,
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    habit = await db.get(Habit, habit_id)
    if not habit:
        raise HTTPException(404, "Habit not found")
    result = await db.execute(
        select(HabitCompletion)
        .where(HabitCompletion.habit_id == habit_id)
        .order_by(HabitCompletion.completed_at.desc())
    )
    return result.scalars().all()
