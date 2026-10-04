from fastapi import APIRouter, Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.drive_schemas import DriveNoteImportRequest
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
