#!/usr/bin/env python3
"""Synthetic runtime acceptance for Drive Knowledge note flows.

Runs from the immutable release backend image against dev-test PostgreSQL. It
exercises the real FastAPI routes and database transaction boundaries, while
replacing only Google content download with a deterministic in-process text
snapshot. It never calls or mutates Google Drive. True Google integration is a
separate acceptance layer and must not be inferred from this script.
"""

from __future__ import annotations

import asyncio
import uuid
from types import SimpleNamespace

import httpx
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.api.auth import current_user
from app.confirmation import CONFIRMATION_HEADER, explicit_confirmation_value
from app.db.session import SessionLocal
from app.main import app
from app.models.drive import DriveDocument, NoteDriveDocument
from app.models.execution_log import ExecutionLog
from app.models.migration_support import EntityTag, Tag
from app.models.note import Note
from app.services import drive_documents
from app.services.idempotency import ACTION_ID_HEADER


ACCEPTANCE_USER_SUB = "acceptance-drive-knowledge-runtime"
ACCEPTANCE_USER = {
    "sub": ACCEPTANCE_USER_SUB,
    "email": "drive-knowledge-acceptance@example.invalid",
    "name": "Drive Knowledge Runtime Acceptance",
}

STAGE_EXIT_CODES = {
    "seed": 61,
    "import": 62,
    "verify_import": 63,
    "reverse_source": 64,
    "manual_attach": 65,
    "reverse_related": 66,
    "source_unlink_guard": 67,
    "manual_detach": 68,
    "note_delete_cleanup": 69,
    "cleanup": 70,
}

IMPORT_FAILURE_EXIT_CODES = {
    "http_contract": 71,
    "integrity": 72,
    "database": 73,
    "unexpected": 74,
}


class AcceptanceStageError(RuntimeError):
    def __init__(self, stage: str, cause: BaseException) -> None:
        super().__init__(f"{stage}: {type(cause).__name__}: {cause}")
        self.stage = stage
        self.cause = cause


def _exit_code_for_stage_error(error: AcceptanceStageError) -> int:
    if error.stage != "import":
        return STAGE_EXIT_CODES.get(error.stage, 1)
    cause = error.cause
    if isinstance(cause, AssertionError):
        return IMPORT_FAILURE_EXIT_CODES["http_contract"]
    if isinstance(cause, IntegrityError):
        return IMPORT_FAILURE_EXIT_CODES["integrity"]
    if isinstance(cause, SQLAlchemyError):
        return IMPORT_FAILURE_EXIT_CODES["database"]
    return IMPORT_FAILURE_EXIT_CODES["unexpected"]


def _failure_category(error: AcceptanceStageError) -> str:
    if error.stage != "import":
        return "stage_failure"
    code = _exit_code_for_stage_error(error)
    for category, category_code in IMPORT_FAILURE_EXIT_CODES.items():
        if code == category_code:
            return category
    return "unexpected"


async def _acceptance_user() -> dict:
    return dict(ACCEPTANCE_USER)


def _expect(response: httpx.Response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(
            f"{label}: expected HTTP {expected}, got {response.status_code}: "
            f"{response.text[:500]}"
        )


def _object(response: httpx.Response, label: str) -> dict:
    payload = response.json()
    if not isinstance(payload, dict):
        raise AssertionError(f"{label}: expected JSON object")
    return payload


def _record(check: str) -> None:
    print(f"drive_knowledge_runtime_check={check}:PASS", flush=True)


async def _seed(document_id: str, google_file_id: str, manual_note_id: str, label: str) -> None:
    async with SessionLocal() as db:
        db.add(
            DriveDocument(
                id=document_id,
                user_sub=ACCEPTANCE_USER_SUB,
                google_file_id=google_file_id,
                name=f"{label} provider file",
                mime_type="application/vnd.google-apps.document",
                web_view_link="https://drive.google.com/file/d/acceptance/view",
                modified_at=None,
            )
        )
        db.add(
            Note(
                id=manual_note_id,
                title=f"{label} related note",
                body="Synthetic related Note for Drive Knowledge acceptance",
                project_id=None,
            )
        )
        await db.commit()


async def _verify_imported_note(
    note_id: str,
    document_id: str,
    expected_tag: str,
    expected_body: str,
) -> None:
    async with SessionLocal() as db:
        note = await db.get(Note, note_id)
        if note is None:
            raise AssertionError("Imported Note was not persisted")
        if note.body != expected_body:
            raise AssertionError("Imported Note did not preserve the one-time snapshot body")
        relation = await db.get(
            NoteDriveDocument,
            {"note_id": note_id, "drive_document_id": document_id},
        )
        if relation is None:
            raise AssertionError("Imported Note did not retain its Drive source relation")
        if relation.relation_type != "source_import" or relation.link_source != "import":
            raise AssertionError("Imported Note source relation metadata is incorrect")
        tag_names = list(
            (
                await db.execute(
                    select(Tag.name)
                    .join(EntityTag, EntityTag.tag_id == Tag.id)
                    .where(
                        EntityTag.entity_type == "note",
                        EntityTag.entity_id == note_id,
                    )
                )
            ).scalars().all()
        )
        if tag_names != [expected_tag]:
            raise AssertionError(f"Imported Note Tags mismatch: {tag_names!r}")


async def _cleanup(
    *,
    document_id: str,
    note_ids: tuple[str, ...],
    tag_name: str,
) -> None:
    async with SessionLocal() as db:
        tag_ids = list(
            (await db.execute(select(Tag.id).where(Tag.name == tag_name))).scalars().all()
        )
        await db.execute(
            delete(NoteDriveDocument).where(
                NoteDriveDocument.drive_document_id == document_id
            )
        )
        await db.execute(
            delete(EntityTag).where(
                EntityTag.entity_type == "note",
                EntityTag.entity_id.in_(note_ids),
            )
        )
        await db.execute(delete(Note).where(Note.id.in_(note_ids)))
        await db.execute(
            delete(DriveDocument).where(
                DriveDocument.id == document_id,
                DriveDocument.user_sub == ACCEPTANCE_USER_SUB,
            )
        )
        await db.execute(
            delete(ExecutionLog).where(ExecutionLog.user_sub == ACCEPTANCE_USER_SUB)
        )
        if tag_ids:
            await db.execute(
                delete(Tag).where(Tag.id.in_(tag_ids), Tag.name == tag_name)
            )
        await db.commit()

    async with SessionLocal() as db:
        if await db.get(DriveDocument, document_id) is not None:
            raise AssertionError("cleanup left acceptance DriveDocument behind")
        for note_id in note_ids:
            if await db.get(Note, note_id) is not None:
                raise AssertionError("cleanup left acceptance Note behind")


async def run_acceptance() -> None:
    run_id = str(uuid.uuid4())
    label = f"[ACCEPTANCE TEST] drive-knowledge {run_id}"
    document_id = str(uuid.uuid4())
    google_file_id = f"acceptance-drive-knowledge-{run_id}"
    manual_note_id = str(uuid.uuid4())
    imported_note_id: str | None = None
    tag_name = f"acceptance-drive-tag-{run_id}"
    snapshot_body = f"Drive one-time snapshot {run_id}"
    original_read_drive_text = drive_documents.read_drive_text
    primary_error: BaseException | None = None
    stage = "seed"

    try:
        await _seed(document_id, google_file_id, manual_note_id, label)

        async def _read_snapshot(_db, user_sub: str, requested_google_file_id: str):
            if user_sub != ACCEPTANCE_USER_SUB:
                raise AssertionError("Drive text acceptance escaped the synthetic user")
            if requested_google_file_id != google_file_id:
                raise AssertionError("Drive text acceptance requested the wrong provider file")
            return SimpleNamespace(
                supported=True,
                text=snapshot_body,
                source_mime_type="application/vnd.google-apps.document",
            )

        drive_documents.read_drive_text = _read_snapshot
        app.dependency_overrides[current_user] = _acceptance_user
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://acceptance.local",
            timeout=30.0,
        ) as client:
            stage = "import"
            response = await client.post(
                f"/api/v1/drive/documents/{document_id}/note-import",
                json={
                    "title": f"{label} imported snapshot",
                    "project_id": None,
                    "tags": [tag_name, tag_name],
                },
                headers={ACTION_ID_HEADER: f"drive-knowledge-import-{run_id}"},
            )
            _expect(response, 201, "Drive Note import")
            imported = _object(response, "Drive Note import")
            imported_note_id = str(imported["id"])
            if imported.get("body") != snapshot_body:
                raise AssertionError("Drive Note import response did not contain snapshot body")
            _record("one_time_import")

            stage = "verify_import"
            await _verify_imported_note(
                imported_note_id,
                document_id,
                tag_name,
                snapshot_body,
            )
            _record("source_relation_and_tags")

            stage = "reverse_source"
            response = await client.get(
                f"/api/v1/drive/notes/{imported_note_id}/documents"
            )
            _expect(response, 200, "Imported Note reverse Drive listing")
            source_relations = response.json()
            if len(source_relations) != 1:
                raise AssertionError("Imported Note did not return exactly one Drive source")
            source = source_relations[0]
            if source.get("relation_type") != "source_import" or source.get("link_source") != "import":
                raise AssertionError("Reverse Drive source metadata mismatch")
            if source.get("document", {}).get("web_view_link") != "https://drive.google.com/file/d/acceptance/view":
                raise AssertionError("Reverse Drive source did not preserve provider link")
            _record("reverse_source_discoverability")

            stage = "manual_attach"
            response = await client.post(
                f"/api/v1/drive/documents/{document_id}/notes/{manual_note_id}",
                headers={ACTION_ID_HEADER: f"drive-knowledge-link-{run_id}"},
            )
            _expect(response, 200, "Manual Drive Note relation")
            relation = _object(response, "Manual Drive Note relation")
            if relation.get("relation_type") != "related" or relation.get("link_source") != "manual":
                raise AssertionError("Manual Drive Note relation metadata mismatch")
            _record("manual_relation")

            stage = "reverse_related"
            response = await client.get(
                f"/api/v1/drive/notes/{manual_note_id}/documents"
            )
            _expect(response, 200, "Manual Note reverse Drive listing")
            related = response.json()
            if len(related) != 1 or related[0].get("relation_type") != "related":
                raise AssertionError("Manual Note reverse Drive relation mismatch")
            _record("reverse_related_discoverability")

            stage = "source_unlink_guard"
            source_target = f"{document_id}:{imported_note_id}"
            response = await client.delete(
                f"/api/v1/drive/documents/{document_id}/notes/{imported_note_id}",
                headers={
                    ACTION_ID_HEADER: f"drive-knowledge-source-unlink-{run_id}",
                    CONFIRMATION_HEADER: explicit_confirmation_value(
                        "drive.document.note.detach",
                        source_target,
                    ),
                },
            )
            _expect(response, 409, "Source import unlink guard")
            _record("source_import_unlink_guard")

            stage = "manual_detach"
            related_target = f"{document_id}:{manual_note_id}"
            response = await client.delete(
                f"/api/v1/drive/documents/{document_id}/notes/{manual_note_id}",
                headers={
                    ACTION_ID_HEADER: f"drive-knowledge-related-unlink-{run_id}",
                    CONFIRMATION_HEADER: explicit_confirmation_value(
                        "drive.document.note.detach",
                        related_target,
                    ),
                },
            )
            _expect(response, 204, "Manual Drive Note unlink")
            async with SessionLocal() as db:
                remaining = await db.get(
                    NoteDriveDocument,
                    {"note_id": manual_note_id, "drive_document_id": document_id},
                )
                if remaining is not None:
                    raise AssertionError("Manual unlink left the relation behind")
                if await db.get(DriveDocument, document_id) is None:
                    raise AssertionError("Manual unlink deleted the Drive document metadata")
            _record("manual_unlink_preserves_document")

            stage = "note_delete_cleanup"
            note_confirmation = explicit_confirmation_value("note.delete", imported_note_id)
            response = await client.delete(
                f"/api/v1/notes/{imported_note_id}",
                headers={CONFIRMATION_HEADER: note_confirmation},
            )
            _expect(response, 204, "Imported Note delete")
            async with SessionLocal() as db:
                source_relation = await db.get(
                    NoteDriveDocument,
                    {"note_id": imported_note_id, "drive_document_id": document_id},
                )
                if source_relation is not None:
                    raise AssertionError("Note delete left Drive source relationship behind")
                if await db.get(DriveDocument, document_id) is None:
                    raise AssertionError("Note delete removed Drive document metadata")
            _record("note_delete_relation_cleanup")

    except BaseException as exc:
        primary_error = AcceptanceStageError(stage, exc)
    finally:
        app.dependency_overrides.pop(current_user, None)
        drive_documents.read_drive_text = original_read_drive_text
        note_ids = tuple(
            note_id for note_id in (manual_note_id, imported_note_id) if note_id is not None
        )
        try:
            await _cleanup(
                document_id=document_id,
                note_ids=note_ids,
                tag_name=tag_name,
            )
            _record("cleanup")
        except BaseException as cleanup_error:
            if primary_error is None:
                raise AcceptanceStageError("cleanup", cleanup_error) from cleanup_error
            print(
                "drive_knowledge_runtime_cleanup_error="
                f"{type(cleanup_error).__name__}",
                flush=True,
            )

    if primary_error is not None:
        raise primary_error

    print("drive_knowledge_runtime_acceptance=PASS", flush=True)


def main() -> int:
    try:
        asyncio.run(run_acceptance())
    except AcceptanceStageError as exc:
        print(
            f"drive_knowledge_runtime_acceptance=FAIL stage={exc.stage} "
            f"category={_failure_category(exc)} error={type(exc.cause).__name__}",
            flush=True,
        )
        return _exit_code_for_stage_error(exc)
    except BaseException as exc:
        print(
            "drive_knowledge_runtime_acceptance=FAIL stage=unknown "
            f"error={type(exc).__name__}",
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
