"""Bounded real-Postgres acceptance for Life tasks 01-03.

No importer execution, no Google access, no user data output. All shopping
fixtures are synthetic and rolled back even on failure. Database reads
do not prove GAS provenance or Sheet row-version parity.
"""
import asyncio
import re
import uuid
from sqlalchemy import select
from fastapi import HTTPException

from app.db.session import SessionLocal
from app.models.curated import CuratedActivity
from app.models.shopping import ShoppingItem, ShoppingList
from app.services.ownership import get_owned, visible_clause


HASH = re.compile(r"^[a-f0-9]{64}$")
MAX_ROWS = 50000

# Expose a coarse failure stage via Cloud Run task exitCode when logging
# is unavailable to the GitHub deployer. Never expose source row contents.
FAILURE_CODES = {
    "handoff_read": 41,
    "handoff_integrity": 42,
    "shopping_mutation": 43,
    "shopping_rollback": 44,
}


async def insert_shopping_fixtures(db, shopping_list, items):
    """Flush the FK parent first; there is no mapped ORM relationship."""
    db.add(shopping_list)
    await db.flush()
    db.add_all(items)
    await db.flush()


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
    try:
        await _run_acceptance()
    except Exception:
        print(f"life_0103_runtime=FAIL category={_acceptance_stage}", flush=True)
        raise SystemExit(FAILURE_CODES[_acceptance_stage])


_acceptance_stage = "handoff_read"


async def _run_acceptance():
    global _acceptance_stage
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
        _acceptance_stage = "handoff_integrity"
        if malformed:
            # No IDs or source text in error messages.
            raise RuntimeError(f"handoff_db_version_malformed_count_{malformed}")
        print(
            f"handoff_pg_consistency=PASS rows={total} malformed={malformed} "
            f"orphan_parent_refs={missing_parent} sheet_parity=NOT_VERIFIED",
            flush=True,
        )
        _acceptance_stage = "shopping_mutation"
        shopping_list = ShoppingList(
            id=list_id, user_sub=own["sub"],
            name="Rollback-only acceptance list", project_id=None
        )
        items_to_create = [
            ShoppingItem(
                id=item_id, list_id=list_id, name=f"Fixture {index}",
                category=None, is_done=False, sort_order=index
            )
            for index, item_id in enumerate(item_ids)
        ]
        try:
            await insert_shopping_fixtures(db, shopping_list, items_to_create)
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
    _acceptance_stage = "shopping_rollback"
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
