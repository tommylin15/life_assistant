import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_, delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.note import Note, NoteLink
from app.models.schemas import NoteCreate, NoteLinkCreate, NoteOut, NoteUpdate
from app.services.execution_log import fail_execution, finish_execution, start_execution

router = APIRouter(prefix="/notes", tags=["notes"])


@router.get("", response_model=list[NoteOut])
async def list_notes(
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Note).order_by(Note.updated_at.desc()))
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
        select(NoteLink)
        .where(
            or_(
                and_(
                    NoteLink.source_note_id == note_id,
                    NoteLink.target_note_id == target_id,
                ),
                and_(
                    NoteLink.source_note_id == target_id,
                    NoteLink.target_note_id == note_id,
                ),
            )
        )
        .limit(1)
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
