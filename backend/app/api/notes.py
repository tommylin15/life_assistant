import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, delete, func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.migration_support import EntityTag, Tag
from app.models.note import Note, NoteLink
from app.models.schemas import (
    NoteCreate,
    NoteLinkCreate,
    NoteOut,
    NoteTagsOut,
    NoteTagsReplace,
    NoteUpdate,
)
from app.services.execution_log import fail_execution, finish_execution, start_execution

router = APIRouter(prefix="/notes", tags=["notes"])

_SEARCH_VECTOR = literal_column(
    "to_tsvector('simple'::regconfig, "
    "coalesce(notes.title, '') || ' ' || coalesce(notes.body, ''))"
)
_SEARCH_CONFIG = literal_column("'simple'::regconfig")


def _note_link_clause(note_id: str, target_id: str):
    return or_(
        and_(
            NoteLink.source_note_id == note_id,
            NoteLink.target_note_id == target_id,
        ),
        and_(
            NoteLink.source_note_id == target_id,
            NoteLink.target_note_id == note_id,
        ),
    )


@router.get("", response_model=list[NoteOut])
async def list_notes(
    q: str | None = Query(default=None, max_length=500),
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (q or "").strip()
    statement = select(Note)
    if query:
        ts_query = func.plainto_tsquery(_SEARCH_CONFIG, query)
        rank = func.ts_rank_cd(_SEARCH_VECTOR, ts_query)
        statement = statement.where(
            or_(
                _SEARCH_VECTOR.op("@@")(ts_query),
                Note.title.icontains(query, autoescape=True),
                Note.body.icontains(query, autoescape=True),
            )
        ).order_by(rank.desc(), Note.updated_at.desc())
    else:
        statement = statement.order_by(Note.updated_at.desc())

    result = await db.execute(statement)
    return result.scalars().all()


@router.post("", response_model=NoteOut, status_code=201)
async def create_note(
    body: NoteCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="note.create",
        provider="life_assistant",
        entity_type="note",
        summary="Create note",
    )
    note = Note(id=str(uuid.uuid4()), **body.model_dump())
    try:
        db.add(note)
        await db.commit()
        await db.refresh(note)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Create note failed")
        raise
    await finish_execution(
        db,
        execution,
        result="created",
        entity_id=note.id,
        summary="Note created",
    )
    return note


@router.get("/{note_id}", response_model=NoteOut)
async def get_note(
    note_id: str,
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    return note


@router.patch("/{note_id}", response_model=NoteOut)
async def update_note(
    note_id: str,
    body: NoteUpdate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="note.update",
        provider="life_assistant",
        entity_type="note",
        entity_id=note_id,
        summary="Update note",
    )
    try:
        for field, value in body.model_dump(exclude_unset=True).items():
            setattr(note, field, value)
        await db.commit()
        await db.refresh(note)
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Update note failed")
        raise
    await finish_execution(
        db,
        execution,
        result="updated",
        summary="Note updated",
    )
    return note


@router.delete("/{note_id}", status_code=204)
async def delete_note(
    note_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="note.delete",
        provider="life_assistant",
        entity_type="note",
        entity_id=note_id,
        summary="Delete note",
    )
    try:
        await db.execute(
            delete(NoteLink).where(
                or_(
                    NoteLink.source_note_id == note_id,
                    NoteLink.target_note_id == note_id,
                )
            )
        )
        await db.execute(
            delete(EntityTag).where(
                EntityTag.entity_type == "note",
                EntityTag.entity_id == note_id,
            )
        )
        await db.delete(note)
        await db.commit()
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Delete note failed")
        raise
    await finish_execution(
        db,
        execution,
        result="deleted",
        summary="Note deleted",
    )


@router.get("/{note_id}/tags", response_model=NoteTagsOut)
async def list_note_tags(
    note_id: str,
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "Note not found")

    result = await db.execute(
        select(Tag.name)
        .join(EntityTag, EntityTag.tag_id == Tag.id)
        .where(
            EntityTag.entity_type == "note",
            EntityTag.entity_id == note_id,
        )
        .order_by(func.lower(Tag.name))
    )
    return NoteTagsOut(tags=list(result.scalars().all()))


@router.put("/{note_id}/tags", response_model=NoteTagsOut)
async def replace_note_tags(
    note_id: str,
    body: NoteTagsReplace,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "Note not found")

    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="note.tags.replace",
        provider="life_assistant",
        entity_type="note",
        entity_id=note_id,
        summary="Replace note tags",
    )
    try:
        await db.execute(
            delete(EntityTag).where(
                EntityTag.entity_type == "note",
                EntityTag.entity_id == note_id,
            )
        )
        for name in body.tags:
            result = await db.execute(
                select(Tag).where(func.lower(Tag.name) == name.casefold()).limit(1)
            )
            tag = result.scalar_one_or_none()
            if tag is None:
                tag = Tag(id=str(uuid.uuid4()), name=name)
                db.add(tag)
                await db.flush()
            db.add(EntityTag(entity_type="note", entity_id=note_id, tag_id=tag.id))
        await db.commit()
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Replace note tags failed")
        raise

    await finish_execution(
        db,
        execution,
        result="updated",
        summary="Note tags replaced",
    )
    return NoteTagsOut(tags=body.tags)


@router.get("/{note_id}/links", response_model=list[NoteOut])
async def list_note_links(
    note_id: str,
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(404, "Note not found")
    result = await db.execute(
        select(NoteLink).where(
            or_(
                NoteLink.source_note_id == note_id,
                NoteLink.target_note_id == note_id,
            )
        )
    )
    linked_ids: set[str] = set()
    for link in result.scalars().all():
        if link.source_note_id != note_id:
            linked_ids.add(link.source_note_id)
        if link.target_note_id != note_id:
            linked_ids.add(link.target_note_id)
    if not linked_ids:
        return []
    notes = await db.execute(
        select(Note).where(Note.id.in_(linked_ids)).order_by(Note.updated_at.desc())
    )
    return notes.scalars().all()


@router.post("/{note_id}/links", status_code=204)
async def create_note_link(
    note_id: str,
    body: NoteLinkCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    target_id = body.target_note_id
    if note_id == target_id:
        raise HTTPException(422, "A note cannot link to itself")

    source = await db.get(Note, note_id)
    if not source:
        raise HTTPException(404, "Note not found")
    target = await db.get(Note, target_id)
    if not target:
        raise HTTPException(404, "Target note not found")

    existing_result = await db.execute(
        select(NoteLink).where(_note_link_clause(note_id, target_id)).limit(1)
    )
    if existing_result.scalar_one_or_none() is not None:
        return None

    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="note.link",
        provider="life_assistant",
        entity_type="note",
        entity_id=note_id,
        summary="Link note",
    )
    try:
        db.add(NoteLink(source_note_id=note_id, target_note_id=target_id))
        await db.commit()
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Link note failed")
        raise
    await finish_execution(
        db,
        execution,
        result="linked",
        summary="Note linked",
    )
    return None


@router.delete("/{note_id}/links/{target_note_id}", status_code=204)
async def delete_note_link(
    note_id: str,
    target_note_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    source = await db.get(Note, note_id)
    if not source:
        raise HTTPException(404, "Note not found")
    target = await db.get(Note, target_note_id)
    if not target:
        raise HTTPException(404, "Target note not found")

    existing_result = await db.execute(
        select(NoteLink).where(_note_link_clause(note_id, target_note_id)).limit(1)
    )
    if existing_result.scalar_one_or_none() is None:
        raise HTTPException(404, "Note link not found")

    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="note.unlink",
        provider="life_assistant",
        entity_type="note",
        entity_id=note_id,
        summary="Unlink note",
    )
    try:
        await db.execute(
            delete(NoteLink).where(_note_link_clause(note_id, target_note_id))
        )
        await db.commit()
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Unlink note failed")
        raise
    await finish_execution(
        db,
        execution,
        result="unlinked",
        summary="Note unlinked",
    )
    return None
