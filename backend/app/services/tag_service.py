import uuid

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.migration_support import EntityTag, Tag


def _normalize_tag_names(names: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for raw in names:
        name = raw.strip()
        if not name:
            continue
        key = name.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(name)
    return normalized


async def list_entity_tags(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
) -> list[str]:
    result = await db.execute(
        select(Tag.name)
        .join(EntityTag, EntityTag.tag_id == Tag.id)
        .where(
            EntityTag.entity_type == entity_type,
            EntityTag.entity_id == entity_id,
        )
        .order_by(func.lower(Tag.name))
    )
    return list(result.scalars().all())


async def _get_or_create_tag(db: AsyncSession, name: str) -> Tag:
    result = await db.execute(
        select(Tag).where(func.lower(Tag.name) == name.casefold()).limit(1)
    )
    tag = result.scalar_one_or_none()
    if tag is not None:
        return tag

    tag = Tag(id=str(uuid.uuid4()), name=name)
    db.add(tag)
    await db.flush()
    return tag


async def replace_entity_tags(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
    names: list[str],
) -> list[str]:
    normalized = _normalize_tag_names(names)
    await db.execute(
        delete(EntityTag).where(
            EntityTag.entity_type == entity_type,
            EntityTag.entity_id == entity_id,
        )
    )
    for name in normalized:
        tag = await _get_or_create_tag(db, name)
        db.add(
            EntityTag(
                entity_type=entity_type,
                entity_id=entity_id,
                tag_id=tag.id,
            )
        )
    return normalized


async def add_entity_tags(
    db: AsyncSession,
    entity_type: str,
    entity_id: str,
    names: list[str],
) -> list[str]:
    existing = await list_entity_tags(db, entity_type, entity_id)
    merged = list(existing)
    seen = {name.casefold() for name in existing}

    for name in _normalize_tag_names(names):
        key = name.casefold()
        if key in seen:
            continue
        tag = await _get_or_create_tag(db, name)
        db.add(
            EntityTag(
                entity_type=entity_type,
                entity_id=entity_id,
                tag_id=tag.id,
            )
        )
        merged.append(name)
        seen.add(key)

    return merged
