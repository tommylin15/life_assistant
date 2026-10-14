import uuid
from collections import defaultdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.schemas import (
    ShoppingItemCreate,
    ShoppingItemsBatchCreate,
    ShoppingItemOut,
    ShoppingItemUpdate,
    ShoppingListCreate,
    ShoppingListOut,
    ShoppingListUpdate,
)
from app.models.shopping import ShoppingItem, ShoppingList
from app.services.ownership import get_owned, require_project, visible_clause
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
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    list_result = await db.execute(
        select(ShoppingList).where(visible_clause(ShoppingList, user)).order_by(ShoppingList.created_at.desc())
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
    await require_project(db, body.project_id, user)
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="shopping_list.create",
        provider="life_assistant",
        entity_type="shopping_list",
        summary="Create shopping list",
    )
    shopping_list = ShoppingList(id=str(uuid.uuid4()), user_sub=user["sub"], **body.model_dump())
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
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    shopping_list = await get_owned(db, ShoppingList, list_id, user, "Shopping list")
    item_result = await db.execute(
        select(ShoppingItem)
        .where(ShoppingItem.list_id == list_id)
        .order_by(ShoppingItem.sort_order, ShoppingItem.id)
    )
    return _shopping_list_out(shopping_list, item_result.scalars().all())


@router.patch("/shopping-lists/{list_id}", response_model=ShoppingListOut)
async def update_shopping_list(
    list_id: str,
    body: ShoppingListUpdate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    shopping_list = await get_owned(db, ShoppingList, list_id, user, "Shopping list")
    if "project_id" in body.model_fields_set:
        await require_project(db, body.project_id, user)
    execution = await start_execution(
        db, user_sub=user["sub"], action_type="shopping_list.update",
        provider="life_assistant", entity_type="shopping_list", entity_id=list_id,
        summary="Update shopping list",
    )
    try:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(shopping_list, field, value)
        await db.commit()
        await db.refresh(shopping_list)
        item_result = await db.execute(
            select(ShoppingItem).where(ShoppingItem.list_id == list_id)
        )
        items = item_result.scalars().all()
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Update shopping list failed")
        raise
    await finish_execution(db, execution, result="updated", summary="Shopping list updated")
    return _shopping_list_out(shopping_list, items)


@router.delete("/shopping-lists/{list_id}", status_code=204)
async def delete_shopping_list(
    list_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    shopping_list = await get_owned(db, ShoppingList, list_id, user, "Shopping list")
    execution = await start_execution(
        db, user_sub=user["sub"], action_type="shopping_list.delete",
        provider="life_assistant", entity_type="shopping_list", entity_id=list_id,
        summary="Delete shopping list",
    )
    try:
        # Items have a non-cascading FK; delete children and parent atomically.
        await db.execute(delete(ShoppingItem).where(ShoppingItem.list_id == list_id))
        await db.delete(shopping_list)
        await db.commit()
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Delete shopping list failed")
        raise
    await finish_execution(db, execution, result="deleted", summary="Shopping list deleted")


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
    shopping_list = await get_owned(db, ShoppingList, list_id, user, "Shopping list")
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


@router.patch("/shopping-items/{item_id}", response_model=ShoppingItemOut)    return item


@router.post(
    "/shopping-lists/{list_id}/items/batch",
    response_model=list[ShoppingItemOut],
    status_code=201,
)
async def create_shopping_items_batch(
    list_id: str,
    body: ShoppingItemsBatchCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await get_owned(db, ShoppingList, list_id, user, "Shopping list")
    execution = await start_execution(
        db, user_sub=user["sub"], action_type="shopping_item.batch_create",
        provider="life_assistant", entity_type="shopping_list", entity_id=list_id,
        summary="Create shopping items batch",
    )
    try:
        result = await db.execute(
            select(func.max(ShoppingItem.sort_order)).where(ShoppingItem.list_id == list_id)
        )
        current_order = result.scalar_one_or_none()
        next_order = current_order + 1 if current_order is not None else 0
        items = [
            ShoppingItem(
                id=str(uuid.uuid4()), list_id=list_id, sort_order=next_order + index,
                **entry.model_dump(),
            )
            for index, entry in enumerate(body.items)
        ]
        db.add_all(items)
        await db.commit()
        for item in items:
            await db.refresh(item)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Create shopping items batch failed")
        raise
    await finish_execution(db, execution, result="created", summary="Shopping items batch created")
    return items


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
    await get_owned(db, ShoppingList, item.list_id, user, "Shopping list")
    toggle_only = body.model_fields_set == {"is_done"}
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="shopping_item.toggle" if toggle_only else "shopping_item.update",
        provider="life_assistant",
        entity_type="shopping_item",
        entity_id=item_id,
        summary="Toggle shopping item" if toggle_only else "Update shopping item",
    )
    try:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(item, field, value)
        await db.commit()
        await db.refresh(item)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Update shopping item failed")
        raise
    await finish_execution(
        db,
        execution,
        result="updated",
        summary="Shopping item toggled" if toggle_only else "Shopping item updated",
    )
    return item


@router.delete("/shopping-items/{item_id}", status_code=204)
async def delete_shopping_item(
    item_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.get(ShoppingItem, item_id)
    if not item:
        raise HTTPException(404, "Shopping item not found")
    await get_owned(db, ShoppingList, item.list_id, user, "Shopping list")
    execution = await start_execution(
        db, user_sub=user["sub"], action_type="shopping_item.delete",
        provider="life_assistant", entity_type="shopping_item", entity_id=item_id,
        summary="Delete shopping item",
    )
    try:
        await db.delete(item)
        await db.commit()
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Delete shopping item failed")
        raise
    await finish_execution(db, execution, result="deleted", summary="Shopping item deleted")
