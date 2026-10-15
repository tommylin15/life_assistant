"""Bounded real-Postgres acceptance for Life tasks 01-03.

No importer execution, no Google access, no user data output. All shopping
fixtures are synthetic and rolled back even on failure. Database reads
do not prove GAS provenance or Sheet row-version parity.
"""
import asyncio
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from fastapi import HTTPException

from app.db.session import SessionLocal
from app.models.curated import CuratedActivity
from app.models.shopping import ShoppingItem, ShoppingList
from app.services.ownership import get_owned, visible_clause


HASH = re.compile(r"^[a-f0-9]{64}$")
MAX_ROWS = 50000


def inspect_handoff(rows):
    """Return only aggregate anomalies, never personally identifiable rows."""
    total, malformed, missing_parent = 0, 0, 0
    known = {r.handoff_event_key for r in rows}
    for row in rows:
        total += 1
        details = row.handoff_details
        if (not isinstance(row.content_hash, str)
            or HASH.fullmatch(row.content_hash) is None
            or not isinstance(details, dict)
            or details.get("event_key") != row.handoff_event_key
            or not details.get("handoff_updated_at_tpe")):
            malformed += 1
        if row.parent_event_key and row.parent_event_key not in known:
            missing_parent += 1
    return total, malformed, missing_parent


async def main():
    nonce = uuid.uuid4().hex
    own = {"sub": "acceptance-shopping-" + nonce}
    other = {"sub": "acceptance-other-" + nonce}
    list_id = str(uuid.uuid4())
    item_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
    async with SessionLocal() as db:
        existing = (await db.execute(
            select(CuratedActivity).where(
                CuratedActivity.handoff_event_key.is_not(None)
            ).limit(MAX_ROWS + 1)
        )).scalars().all()
        if len(existing) > MAX_ROWS:
            raise RuntimeError("handoff_db_readback_bounded_limit")
        total, malformed, missing_parent = inspect_handoff(existing)
        if malformed:
            # No IDs or source text in error messages.
            raise RuntimeError(f"handoff_db_version_malformed_count_{malformed}")
        print(
            f"handoff_pg_consistency=PASS rows={total} malformed={malformed} "
            f"orphan_parent_refs={missing_parent} sheet_parity=NOT_VERIFIED",
            flush=True,
        )
        shopping_list = ShoppingList(
            id=list_id, user_sub=own["sub"],
            name="Rollback-only acceptance list", project_id=None
        )
        db.add(shopping_list)
        for index, item_id in enumerate(item_ids):
            db.add(ShoppingItem(
                id=item_id, list_id=list_id, name=f"Fixture {index}",
                category=None, is_done=False, sort_order=index
            ))
        try:
            await db.flush()
            items = (await db.execute(
                select(ShoppingItem).where(ShoppingItem.list_id == list_id)
                .order_by(ShoppingItem.sort_order, ShoppingItem.id)
            )).scalars().all()
            if [item.id for item in items] != item_ids:
                raise RuntimeError("shopping_order_readback_failed")
            items[0].name = "Edited fixture"
            items[1].is_done = True
            await db.flush()
            fetched = await db.get(ShoppingItem, item_ids[0])
            if fetched is None or fetched.name != "Edited fixture":
                raise RuntimeError("shopping_edit_readback_failed")
            own_read = await db.scalar(select(ShoppingList).where(
                ShoppingList.id == list_id, visible_clause(ShoppingList, own)))
            hidden = await db.scalar(select(ShoppingList).where(
                ShoppingList.id == list_id, visible_clause(ShoppingList, other)))
            if own_read is None or hidden is not None:
                raise RuntimeError("shopping_owner_isolation_failed")
            try:
                await get_owned(db, ShoppingList, list_id, other, "Shopping list")
            except HTTPException as exc:
                if exc.status_code != 404:
                    raise
            else:
                raise RuntimeError("shopping_foreign_mutation_would_be_allowed")
            await db.delete(items[0])
            await db.flush()
            remaining = (await db.execute(select(ShoppingItem).where(
                ShoppingItem.list_id == list_id))).scalars().all()
            if len(remaining) != 1 or remaining[0].id != item_ids[1]:
                raise RuntimeError("shopping_item_delete_readback_failed")
        finally:
            await db.rollback()
    async with SessionLocal() as db:
        if await db.get(ShoppingList, list_id) is not None:
            raise RuntimeError("shopping_fixture_list_not_rolled_back")
        for item_id in item_ids:
            if await db.get(ShoppingItem, item_id) is not None:
                raise RuntimeError("shopping_fixture_item_not_rolled_back")
    print("shopping_runtime=PASS edit_delete_batch_order_owner_isolation rollback_only=true", flush=True)
    print("life_0103_runtime=PASS external_gas_sheet_calendar_ux=NOT_VERIFIED", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
