from typing import Literal

from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.errors import ApiError
from app.models.drive import DriveDocument, NoteDriveDocument
from app.models.drive_schemas import DriveDocumentOut, DriveNoteImportRequest
from app.models.note import Note
from app.models.schemas import NoteOut
from app.services import drive_documents
from app.services.execution_log import fail_execution
from app.services.idempotency import (
    ACTION_ID_HEADER,
    commit_reserved_execution,
    replay_entity,
    reserve_execution,
)

router = APIRouter(prefix="/drive", tags=["drive"])


class DriveNoteRelationOut(BaseModel):
    note: NoteOut
    relation_type: Literal["source_import", "related"]
    link_source: Literal["manual", "ai_accepted", "import"]


class NoteDriveRelationOut(BaseModel):
    document: DriveDocumentOut
    relation_type: Literal["source_import", "related"]
    link_source: Literal["manual", "ai_accepted", "import"]


def _note_relation_out(note: Note, relation: NoteDriveDocument) -> DriveNoteRelationOut:
    return DriveNoteRelationOut(
        note=NoteOut.model_validate(note),
        relation_type=relation.relation_type,
        link_source=relation.link_source,
    )


def _document_relation_out(
    document: DriveDocument,
    relation: NoteDriveDocument,
) -> NoteDriveRelationOut:
    return NoteDriveRelationOut(
        document=DriveDocumentOut.model_validate(document),
        relation_type=relation.relation_type,
        link_source=relation.link_source,
    )


@router.post(
    "/documents/{document_id}/note-import",
    response_model=NoteOut,
    status_code=201,
)
async def import_drive_document_note(
    document_id: str,
    body: DriveNoteImportRequest,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    action_id: str | None = Header(default=None, alias=ACTION_ID_HEADER),
):
    payload = {
        "document_id": document_id,
        **body.model_dump(mode="json"),
    }
    reservation = await reserve_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.document.note_import",
        action_id=action_id,
        request_payload=payload,
        provider="google",
        entity_type="note",
        summary="Import Drive document snapshot to Note",
    )
    if reservation.is_replay:
        return await replay_entity(db, reservation, Note)

    try:
        note = await drive_documents.import_document_to_note(
            db,
            user["sub"],
            document_id,
            title=body.title,
            project_id=body.project_id,
            tags=body.tags,
        )
    except Exception as exc:
        await fail_execution(
            db,
            reservation.execution,
            exc,
            summary="Drive document Note import failed",
        )
        raise

    await commit_reserved_execution(
        db,
        reservation,
        result="created",
        entity_type="note",
        entity_id=note.id,
        summary="Drive document snapshot imported to Note",
        failure_summary="Drive document Note import failed",
        refresh_entity=note,
    )
    return note


@router.get(
    "/documents/{document_id}/notes",
    response_model=list[DriveNoteRelationOut],
)
async def list_drive_document_notes(
    document_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    relations = await drive_documents.list_document_note_relations(
        db,
        user["sub"],
        document_id,
    )
    return [_note_relation_out(note, relation) for note, relation in relations]


@router.get(
    "/notes/{note_id}/documents",
    response_model=list[NoteDriveRelationOut],
)
async def list_note_drive_documents(
    note_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    relations = await drive_documents.list_note_document_relations(
        db,
        user["sub"],
        note_id,
    )
    return [
        _document_relation_out(document, relation)
        for document, relation in relations
    ]


@router.post(
    "/documents/{document_id}/notes/{note_id}",
    response_model=DriveNoteRelationOut,
)
async def attach_drive_document_note(
    document_id: str,
    note_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    action_id: str | None = Header(default=None, alias=ACTION_ID_HEADER),
):
    payload = {"document_id": document_id, "note_id": note_id}
    reservation = await reserve_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.document.note.attach",
        action_id=action_id,
        request_payload=payload,
        provider="internal",
        entity_type="drive_note_relation",
        entity_id=document_id,
        summary="Relate Drive document to Note",
    )

    if reservation.is_replay:
        await drive_documents.get_document(db, user["sub"], document_id)
        note = await db.get(Note, note_id)
        relation = await db.get(
            NoteDriveDocument,
            {"note_id": note_id, "drive_document_id": document_id},
        )
        if note is None or relation is None:
            raise ApiError(
                409,
                "idempotency_result_unavailable",
                "The previous Drive Note relationship is no longer available",
            )
        return _note_relation_out(note, relation)

    try:
        relation, created = await drive_documents.attach_document_note(
            db,
            user["sub"],
            document_id,
            note_id,
        )
        note = await db.get(Note, note_id)
        if note is None:
            raise ApiError(409, "note_unavailable", "Note became unavailable")
    except Exception as exc:
        await fail_execution(
            db,
            reservation.execution,
            exc,
            summary="Drive document Note relation failed",
        )
        raise

    await commit_reserved_execution(
        db,
        reservation,
        result="attached" if created else "existing",
        entity_type="drive_note_relation",
        entity_id=document_id,
        summary=(
            "Drive document related to Note"
            if created
            else "Drive document Note relation already exists"
        ),
        failure_summary="Drive document Note relation failed",
    )
    return _note_relation_out(note, relation)


@router.delete("/documents/{document_id}/notes/{note_id}", status_code=204)
async def detach_drive_document_note(
    document_id: str,
    note_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    action_id: str | None = Header(default=None, alias=ACTION_ID_HEADER),
):
    payload = {"document_id": document_id, "note_id": note_id}
    reservation = await reserve_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.document.note.detach",
        action_id=action_id,
        request_payload=payload,
        provider="internal",
        entity_type="drive_note_relation",
        entity_id=document_id,
        summary="Unlink Drive document and Note",
    )
    if reservation.is_replay:
        return Response(status_code=204)

    try:
        removed = await drive_documents.detach_document_note(
            db,
            user["sub"],
            document_id,
            note_id,
        )
    except Exception as exc:
        await fail_execution(
            db,
            reservation.execution,
            exc,
            summary="Drive document Note unlink failed",
        )
        raise

    await commit_reserved_execution(
        db,
        reservation,
        result="detached" if removed else "already_absent",
        entity_type="drive_note_relation",
        entity_id=document_id,
        summary=(
            "Drive document unlinked from Note"
            if removed
            else "Drive document Note relation already absent"
        ),
        failure_summary="Drive document Note unlink failed",
    )
    return Response(status_code=204)
