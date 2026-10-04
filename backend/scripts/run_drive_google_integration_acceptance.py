#!/usr/bin/env python3
"""Optional real Google Drive integration acceptance.

This layer is intentionally separate from synthetic runtime acceptance. It runs
only when DRIVE_ACCEPTANCE_USER_SUB and DRIVE_ACCEPTANCE_GOOGLE_FILE_ID identify
an already-authorized user and a harmless file that the user explicitly chose
through Google Picker. The script uses only the existing drive.file grant,
never broadens OAuth scope, never changes provider content, and removes only
rows it creates locally.
"""

from __future__ import annotations

import asyncio
import os
import uuid

from sqlalchemy import delete, select

from app.db.session import SessionLocal
from app.models.drive import DriveDocument, NoteDriveDocument
from app.models.google_integration import GoogleConnection
from app.models.migration_support import EntityTag, Tag
from app.models.note import Note
from app.services import drive_documents
from app.services.google_drive_files import get_drive_file_metadata, read_drive_text
from app.services.google_oauth import SERVICE_SCOPES


REQUIRED_SCOPE = SERVICE_SCOPES["drive"][0]


class IntegrationError(RuntimeError):
    pass


def _fixture() -> tuple[str, str] | None:
    user_sub = os.environ.get("DRIVE_ACCEPTANCE_USER_SUB", "").strip()
    google_file_id = os.environ.get("DRIVE_ACCEPTANCE_GOOGLE_FILE_ID", "").strip()
    if not user_sub or not google_file_id:
        return None
    return user_sub, google_file_id


def _record(check: str) -> None:
    print(f"drive_google_integration_check={check}:PASS", flush=True)


async def _cleanup(
    *,
    note_id: str | None,
    document_id: str | None,
    delete_document: bool,
    tag_name: str,
) -> None:
    async with SessionLocal() as db:
        if note_id:
            await db.execute(
                delete(NoteDriveDocument).where(NoteDriveDocument.note_id == note_id)
            )
            await db.execute(
                delete(EntityTag).where(
                    EntityTag.entity_type == "note",
                    EntityTag.entity_id == note_id,
                )
            )
            await db.execute(delete(Note).where(Note.id == note_id))
        tag_ids = list(
            (await db.execute(select(Tag.id).where(Tag.name == tag_name))).scalars().all()
        )
        if tag_ids:
            await db.execute(delete(Tag).where(Tag.id.in_(tag_ids), Tag.name == tag_name))
        if delete_document and document_id:
            await db.execute(
                delete(NoteDriveDocument).where(
                    NoteDriveDocument.drive_document_id == document_id
                )
            )
            await db.execute(delete(DriveDocument).where(DriveDocument.id == document_id))
        await db.commit()


async def run_acceptance(user_sub: str, google_file_id: str) -> None:
    run_id = str(uuid.uuid4())
    tag_name = f"acceptance-real-drive-{run_id}"
    note_id: str | None = None
    document_id: str | None = None
    delete_document = False
    primary_error: BaseException | None = None

    try:
        async with SessionLocal() as db:
            connection = await db.get(GoogleConnection, user_sub)
            if connection is None:
                raise IntegrationError("configured acceptance user has no Google connection")
            if REQUIRED_SCOPE not in set(connection.scopes.split()):
                raise IntegrationError("configured acceptance user lacks drive.file scope")
            _record("drive_file_scope_present")

            existing = (
                await db.execute(
                    select(DriveDocument).where(
                        DriveDocument.user_sub == user_sub,
                        DriveDocument.google_file_id == google_file_id,
                    )
                )
            ).scalar_one_or_none()

            metadata = await get_drive_file_metadata(db, user_sub, google_file_id)
            if metadata.id != google_file_id:
                raise IntegrationError("Google metadata returned a mismatched file id")
            _record("real_google_metadata")

            snapshot = await read_drive_text(db, user_sub, google_file_id)
            if not snapshot.supported or snapshot.text is None:
                raise IntegrationError(
                    "Picker acceptance fixture must be a readable Drive text document"
                )
            _record("real_google_readable_content")

            documents = await drive_documents.register_documents(
                db,
                user_sub,
                [google_file_id],
            )
            if len(documents) != 1:
                raise IntegrationError("Drive registration did not return exactly one document")
            document = documents[0]
            document_id = document.id
            delete_document = existing is None
            await db.commit()
            _record("picker_selected_file_registered")

        async with SessionLocal() as db:
            note = await drive_documents.import_document_to_note(
                db,
                user_sub,
                document_id,
                title=f"[ACCEPTANCE TEST] real Drive snapshot {run_id}",
                project_id=None,
                tags=[tag_name],
            )
            note_id = note.id
            await db.commit()
            await db.refresh(note)
            if note.body != snapshot.text:
                raise IntegrationError("Imported Note did not equal real Drive snapshot")
            relations = await drive_documents.list_note_document_relations(
                db,
                user_sub,
                note.id,
            )
            if len(relations) != 1:
                raise IntegrationError("Imported Note did not expose one Drive source")
            source_document, relation = relations[0]
            if source_document.google_file_id != google_file_id:
                raise IntegrationError("Imported Note source points at the wrong Drive file")
            if relation.relation_type != "source_import" or relation.link_source != "import":
                raise IntegrationError("Imported Note source relation metadata mismatch")
            _record("real_drive_one_time_note_import")
            _record("source_link_returns_to_picker_file")

    except BaseException as exc:
        primary_error = exc
    finally:
        try:
            await _cleanup(
                note_id=note_id,
                document_id=document_id,
                delete_document=delete_document,
                tag_name=tag_name,
            )
            _record("cleanup_local_rows_only")
        except BaseException as cleanup_error:
            if primary_error is None:
                primary_error = cleanup_error
            else:
                print(
                    "drive_google_integration_cleanup_error="
                    f"{type(cleanup_error).__name__}:{cleanup_error}",
                    flush=True,
                )

    if primary_error is not None:
        raise primary_error

    print("drive_google_integration_acceptance=PASS", flush=True)


def main() -> int:
    fixture = _fixture()
    if fixture is None:
        print(
            "drive_google_integration_acceptance=NOT_VERIFIED "
            "reason=picker_selected_fixture_not_configured",
            flush=True,
        )
        return 0
    try:
        asyncio.run(run_acceptance(*fixture))
    except BaseException as exc:
        print(
            "drive_google_integration_acceptance=FAIL "
            f"error={type(exc).__name__}:{exc}",
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
