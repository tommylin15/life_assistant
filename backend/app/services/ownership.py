"""Per-user ownership; legacy NULL resources remain Owner-only, never shared."""
import os
from fastapi import HTTPException
from sqlalchemy import or_


def legacy_owner(user: dict) -> bool:
    configured = os.environ.get("ALLOWED_GOOGLE_EMAIL", "").strip().casefold()
    # Fail closed when Owner identity is not configured: legacy NULL rows
    # must never become globally readable, including in misconfigured stages.
    return bool(configured) and str(user.get("email", "")).strip().casefold() == configured


def visible_clause(model, user: dict):
    owned = model.user_sub == user["sub"]
    return or_(owned, model.user_sub.is_(None)) if legacy_owner(user) else owned


def can_access(item, user: dict) -> bool:
    return item is not None and (
        item.user_sub == user["sub"] or
        (item.user_sub is None and legacy_owner(user))
    )


async def get_owned(db, model, entity_id: str, user: dict, label: str):
    entity = await db.get(model, entity_id)
    if not can_access(entity, user):
        raise HTTPException(404, f"{label} not found")
    return entity


async def require_project(db, project_id: str | None, user: dict):
    if project_id is not None:
        from app.models.project import Project
        await get_owned(db, Project, project_id, user, "Project")
