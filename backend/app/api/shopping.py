import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.schemas import (
    ShoppingItemCreate,
    ShoppingItemOut,
    ShoppingItemUpdate,
    ShoppingListCreate,
    ShoppingListOut,
)
from app.models.shopping import ShoppingItem, ShoppingList
from app.services.execution_log import fail_execution, finish_execution, start_execution

router = APIRouter(tags=["shopping"])


def _shopping_list_out(
    shopping_list: ShoppingList,
    items: list[ShoppingItem],
) -> ShoppingListOut:
    ordered_items = sorted(items, key=lambda item: (item.sort_order, item.id))
    return ShoppingListOut(
        id=shopping_list.id,
        name=shopping_list.name,
        project_id=shopping_list.project_id,
        created_at=shopping_list.created_at,
        items=ordered_items,
    )


@router.get("/shopping-lists", response_model=list[ShoppingListOut])
async def list_shopping_lists(
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    list_result = await db.execute(
        select(ShoppingList).order_by(ShoppingList.created_at.desc())
    )
    shopping_lists = list_result.scalars().all()
    if not shopping_lists:
        return []

    list_ids = [shopping_list.id for shopping_list in shopping_lists]
    item_result = await db.execute(
        select(ShoppingItem)
        .where(ShoppingItem.list_id.in_(list_ids))
        .order_by(ShoppingItem.sort_order, ShoppingItem.id)
    )
    items_by_list: dict[str, list[ShoppingItem]] = defaultdict(list)
    for item in item_result.scalars().all():
        items_by_list[item.list_id].append(item)

    return [
        _shopping_list_out(shopping_list, items_by_list[shopping_list.id])
        for shopping_list in shopping_lists
    ]


@router.post("/shopping-lists", response_model=ShoppingListOut, status_code=201)
async def create_shopping_list(
    body: ShoppingListCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="shopping_list.create",
        provider="life_assistant",
        entity_type="shopping_list",
        summary="Create shopping list",
    )
    shopping_list = ShoppingList(id=str(uuid.uuid4()), **body.model_dump())
    try:
        db.add(shopping_list)
        await db.commit()
        await db.refresh(shopping_list)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Create shopping list failed")
        raise
    await finish_execution(
        db,
        execution,
        result="created",
        entity_id=shopping_list.id,
        summary="Shopping list created",
    )
    return _shopping_list_out(shopping_list, [])


@router.get("/shopping-lists/{list_id}", response_model=ShoppingListOut)
async def get_shopping_list(
    list_id: str,
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    shopping_list = await db.get(ShoppingList, list_id)
    if not shopping_list:
        raise HTTPException(404, "Shopping list not found")
    item_result = await db.execute(
        select(ShoppingItem)
        .where(ShoppingItem.list_id == list_id)
        .order_by(ShoppingItem.sort_order, ShoppingItem.id)
    )
    return _shopping_list_out(shopping_list, item_result.scalars().all())


@router.post(
    "/shopping-lists/{list_id}/items",
    response_model=ShoppingItemOut,
    status_code=201,
)
async def create_shopping_item(
    list_id: str,
    body: ShoppingItemCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    shopping_list = await db.get(ShoppingList, list_id)
    if not shopping_list:
        raise HTTPException(404, "Shopping list not found")
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="shopping_item.create",
        provider="life_assistant",
        entity_type="shopping_item",
        summary="Create shopping item",
    )
    item = ShoppingItem(id=str(uuid.uuid4()), list_id=list_id, **body.model_dump())
    try:
        db.add(item)
        await db.commit()
        await db.refresh(item)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Create shopping item failed")
        raise
    await finish_execution(
        db,
        execution,
        result="created",
        entity_id=item.id,
        summary="Shopping item created",
    )
    return item


@router.patch("/shopping-items/{item_id}", response_model=ShoppingItemOut)
async def update_shopping_item(
    item_id: str,
    body: ShoppingItemUpdate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(ShoppingItem, item_id)
    if not item:
        raise HTTPException(404, "Shopping item not found")
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="shopping_item.toggle",
        provider="life_assistant",
        entity_type="shopping_item",
        entity_id=item_id,
        summary="Toggle shopping item",
    )
    try:
        item.is_done = body.is_done
        await db.commit()
        await db.refresh(item)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Toggle shopping item failed")
        raise
    await finish_execution(
        db,
        execution,
        result="updated",
        summary="Shopping item toggled",
    )
    return item
