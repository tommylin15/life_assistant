"""Rollback-only private tenancy readback against the actual PostgreSQL schema.

Never commits test rows. Every tenant's listed rows must be its own.
"""
import asyncio
import uuid

from fastapi import HTTPException
from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.project import Project
from app.models.note import Note
from app.models.habit import Habit
from app.models.shopping import ShoppingList
from app.services.ownership import get_owned, visible_clause
from scripts.apply_cloud_domain_parity_release import RELEASE_TARGET_REVISION
from sqlalchemy import text


async def main():
    nonce = uuid.uuid4().hex
    own = {"sub": "acceptance-owner-" + nonce, "email": "tenant-a@example.invalid"}
    foreign = {"sub": "acceptance-foreign-" + nonce, "email": "tenant-b@example.invalid"}
    rows = [
        Project(id=str(uuid.uuid4()), name="Synthetic tenancy project", user_sub=own["sub"]),
        Note(id=str(uuid.uuid4()), title="Synthetic tenancy note", body="Fixture",
             user_sub=own["sub"]),
        Habit(id=str(uuid.uuid4()), title="Synthetic tenancy habit",
              recurrence_rule="daily", user_sub=own["sub"]),
        ShoppingList(id=str(uuid.uuid4()), name="Synthetic tenancy shopping",
                     user_sub=own["sub"]),
    ]
    try:
        async with SessionLocal() as db:
            try:
                revision = await db.scalar(text("SELECT version_num FROM alembic_version"))
                if revision != RELEASE_TARGET_REVISION:
                    raise RuntimeError("tenant_schema_revision_mismatch")
                db.add_all(rows)
                await db.flush()
                for row in rows:
                    model = type(row)
                    own_read = await db.scalar(select(model).where(
                        model.id == row.id, visible_clause(model, own)))
                    foreign_read = await db.scalar(select(model).where(
                        model.id == row.id, visible_clause(model, foreign)))
                    if own_read is None or foreign_read is not None:
                        raise RuntimeError(f"tenant_readback_failed:{model.__tablename__}")
                    try:
                        await get_owned(db, model, row.id, foreign, "Resource")
                    except HTTPException as err:
                        if err.status_code != 404:
                            raise
                    else:
                        raise RuntimeError(f"tenant_direct_access_failed:{model.__tablename__}")
            finally:
                await db.rollback()
        async with SessionLocal() as db:
            for row in rows:
                if await db.get(type(row), row.id) is not None:
                    raise RuntimeError(f"tenant_rollback_failed:{type(row).__tablename__}")
        print("tenant_ownership=PASS rollback_only=true tables=notes,projects,habits,shopping_lists")
    except Exception:
        print("tenant_ownership=FAIL rollback_only_required=true")
        raise


if __name__ == "__main__":
    asyncio.run(main())
