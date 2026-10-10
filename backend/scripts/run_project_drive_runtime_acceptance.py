#!/usr/bin/env python3
"""Runtime acceptance for Project ↔ Drive-document relationships.

This acceptance runs from the exact release backend image against the dev-test
PostgreSQL database. It exercises the real FastAPI routes with a fixed synthetic
identity and seeds only one synthetic DriveDocument row directly in PostgreSQL,
so it never calls or mutates Google Drive. Every created row is tracked by exact
ID and removed in a finally path.
"""

from __future__ import annotations

import asyncio
import uuid

import httpx
from sqlalchemy import delete, select

from app.api.auth import current_user
from app.confirmation import CONFIRMATION_HEADER, explicit_confirmation_value
from app.db.session import SessionLocal
from app.main import app, CORE_FEATURE_GATES, DRIVE_FEATURE_GATE
from app.models.drive import DriveDocument, ProjectDriveDocument
from app.models.project import Project
from app.services.idempotency import ACTION_ID_HEADER


ACCEPTANCE_USER_SUB = "acceptance-project-drive-runtime"
ACCEPTANCE_USER = {
    "sub": ACCEPTANCE_USER_SUB,
    "email": "project-drive-acceptance@example.invalid",
    "name": "Project Drive Runtime Acceptance",
}

STAGE_EXIT_CODES = {
    "seed_drive_document": 21,
    "project_create": 22,
    "list_empty_before_attach": 23,
    "attach": 24,
    "attach_replay": 25,
    "repeat_attach": 26,
    "list_after_attach": 27,
    "project_delete_guard": 28,
    "detach": 29,
    "list_empty_after_detach": 30,
    "project_delete_after_detach": 31,
    "cleanup": 32,
}


class AcceptanceStageError(RuntimeError):
    def __init__(self, stage: str, cause: BaseException) -> None:
        super().__init__(f"{stage}: {type(cause).__name__}: {cause}")
        self.stage = stage
        self.cause = cause


async def _acceptance_user() -> dict:
    return dict(ACCEPTANCE_USER)


def _expect(response: httpx.Response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(
            f"{label}: expected HTTP {expected}, got {response.status_code}: "
            f"{response.text[:500]}"
        )


def _json_object(response: httpx.Response, label: str) -> dict:
    try:
        payload = response.json()
    except ValueError as exc:
        raise AssertionError(f"{label}: response was not JSON") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"{label}: expected JSON object")
    return payload


def _error_message(response: httpx.Response, label: str) -> str:
    payload = _json_object(response, label)
    error = payload.get("error")
    if not isinstance(error, dict):
        raise AssertionError(f"{label}: expected shared error envelope")
    message = error.get("message")
    if not isinstance(message, str) or not message:
        raise AssertionError(f"{label}: expected non-empty error.message")
    return message


def _record(check: str) -> None:
    print(f"project_drive_runtime_check={check}:PASS", flush=True)


async def _seed_drive_document(document_id: str, google_file_id: str, label: str) -> None:
    async with SessionLocal() as db:
        db.add(
            DriveDocument(
                id=document_id,
                user_sub=ACCEPTANCE_USER_SUB,
                google_file_id=google_file_id,
                name=f"{label} Drive document",
                mime_type="text/plain",
                web_view_link=None,
                modified_at=None,
            )
        )
        await db.commit()


async def _verify_relation_count(project_id: str, document_id: str, expected: int) -> None:
    async with SessionLocal() as db:
        result = await db.execute(
            select(ProjectDriveDocument).where(
                ProjectDriveDocument.project_id == project_id,
                ProjectDriveDocument.drive_document_id == document_id,
            )
        )
        actual = len(list(result.scalars().all()))
        if actual != expected:
            raise AssertionError(
                f"Project Drive relation count mismatch: expected {expected}, got {actual}"
            )


async def _verify_document_survives(document_id: str) -> None:
    async with SessionLocal() as db:
        document = await db.get(DriveDocument, document_id)
        if document is None:
            raise AssertionError("DriveDocument was deleted while only detaching Project relation")


async def _cleanup(project_id: str | None, document_id: str) -> None:
    """Delete only exact acceptance IDs, in FK-safe order."""

    async with SessionLocal() as db:
        await db.execute(
            delete(ProjectDriveDocument).where(
                ProjectDriveDocument.drive_document_id == document_id
            )
        )
        if project_id is not None:
            await db.execute(delete(Project).where(Project.id == project_id))
        await db.execute(
            delete(DriveDocument).where(
                DriveDocument.id == document_id,
                DriveDocument.user_sub == ACCEPTANCE_USER_SUB,
            )
        )
        await db.commit()

    async with SessionLocal() as db:
        if await db.get(DriveDocument, document_id) is not None:
            raise AssertionError("cleanup left acceptance DriveDocument behind")
        if project_id is not None and await db.get(Project, project_id) is not None:
            raise AssertionError("cleanup left acceptance Project behind")


async def run_acceptance() -> None:
    run_id = str(uuid.uuid4())
    label = f"[ACCEPTANCE TEST] project-drive {run_id}"
    document_id = str(uuid.uuid4())
    google_file_id = f"acceptance-drive-file-{run_id}"
    project_id: str | None = None
    primary_error: BaseException | None = None
    stage = "seed_drive_document"

    try:
        await _seed_drive_document(document_id, google_file_id, label)
        app.dependency_overrides[current_user] = _acceptance_user
        # Test relationships independently of admin rollout in this isolated runner.
        app.dependency_overrides[CORE_FEATURE_GATES["projects"]] = lambda: None
        app.dependency_overrides[DRIVE_FEATURE_GATE] = lambda: None
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://acceptance.local",
            timeout=30.0,
        ) as client:
            stage = "project_create"
            response = await client.post(
                "/api/v1/projects",
                json={"name": f"{label} Project", "summary": label, "status": "active"},
                headers={ACTION_ID_HEADER: f"project-drive-project-create-{run_id}"},
            )
            _expect(response, 201, "Project create")
            project_id = str(_json_object(response, "Project create")["id"])
            _record("project_create")

            stage = "list_empty_before_attach"
            response = await client.get(
                "/api/v1/drive/project-documents",
                params={"project_id": project_id},
            )
            _expect(response, 200, "Project Drive list before attach")
            payload = _json_object(response, "Project Drive list before attach")
            if payload.get("returned") != 0 or payload.get("documents") != []:
                raise AssertionError("Project Drive list was not empty before attach")
            _record("list_empty_before_attach")

            stage = "attach"
            attach_headers = {
                ACTION_ID_HEADER: f"project-drive-attach-{run_id}",
            }
            response = await client.post(
                f"/api/v1/drive/documents/{document_id}/projects",
                json={"project_ids": [project_id, project_id]},
                headers=attach_headers,
            )
            _expect(response, 200, "Drive document attach")
            attach_payload = _json_object(response, "Drive document attach")
            if attach_payload.get("project_ids") != [project_id] or attach_payload.get("returned") != 1:
                raise AssertionError("Drive document attach response mismatch")
            _record("attach")

            # Exact action-id replay must remain safe.
            stage = "attach_replay"
            response = await client.post(
                f"/api/v1/drive/documents/{document_id}/projects",
                json={"project_ids": [project_id, project_id]},
                headers=attach_headers,
            )
            _expect(response, 200, "Drive document attach replay")

            # A second logical attach with a fresh action id must also remain
            # relation-idempotent because the join table has a composite PK.
            stage = "repeat_attach"
            response = await client.post(
                f"/api/v1/drive/documents/{document_id}/projects",
                json={"project_ids": [project_id]},
                headers={ACTION_ID_HEADER: f"project-drive-attach-repeat-{run_id}"},
            )
            _expect(response, 200, "Drive document repeat attach")
            await _verify_relation_count(project_id, document_id, 1)
            _record("repeat_attach_idempotent")

            stage = "list_after_attach"
            response = await client.get(
                "/api/v1/drive/project-documents",
                params={"project_id": project_id},
            )
            _expect(response, 200, "Project Drive list after attach")
            payload = _json_object(response, "Project Drive list after attach")
            documents = payload.get("documents") or []
            if payload.get("returned") != 1 or [item.get("id") for item in documents] != [document_id]:
                raise AssertionError("Attached Drive document was not returned exactly once")
            _record("list_after_attach")

            stage = "project_delete_guard"
            project_confirmation = explicit_confirmation_value("project.delete", project_id)
            response = await client.delete(
                f"/api/v1/projects/{project_id}",
                headers={CONFIRMATION_HEADER: project_confirmation},
            )
            _expect(response, 409, "Project delete guard for Drive relation")
            message = _error_message(response, "Project delete guard for Drive relation")
            if message != "Project has linked Drive documents":
                raise AssertionError(f"Unexpected Project delete guard message: {message!r}")
            _record("project_delete_guard")

            stage = "detach"
            detach_target = f"{document_id}:{project_id}"
            response = await client.delete(
                f"/api/v1/drive/documents/{document_id}/projects/{project_id}",
                headers={
                    ACTION_ID_HEADER: f"project-drive-detach-{run_id}",
                    CONFIRMATION_HEADER: explicit_confirmation_value(
                        "drive.document.project.detach",
                        detach_target,
                    ),
                },
            )
            _expect(response, 204, "Drive document detach")
            await _verify_relation_count(project_id, document_id, 0)
            await _verify_document_survives(document_id)
            _record("detach_preserves_drive_document")

            stage = "list_empty_after_detach"
            response = await client.get(
                "/api/v1/drive/project-documents",
                params={"project_id": project_id},
            )
            _expect(response, 200, "Project Drive list after detach")
            payload = _json_object(response, "Project Drive list after detach")
            if payload.get("returned") != 0 or payload.get("documents") != []:
                raise AssertionError("Project Drive list was not empty after detach")
            _record("list_empty_after_detach")

            stage = "project_delete_after_detach"
            response = await client.delete(
                f"/api/v1/projects/{project_id}",
                headers={CONFIRMATION_HEADER: project_confirmation},
            )
            _expect(response, 204, "Project delete after detach")
            await _verify_document_survives(document_id)
            _record("project_delete_after_detach_preserves_document")

    except BaseException as exc:
        primary_error = AcceptanceStageError(stage, exc)
    finally:
        app.dependency_overrides.pop(current_user, None)
        app.dependency_overrides.pop(CORE_FEATURE_GATES["projects"], None)
        app.dependency_overrides.pop(DRIVE_FEATURE_GATE, None)
        try:
            await _cleanup(project_id, document_id)
            _record("cleanup")
        except BaseException as cleanup_error:
            if primary_error is None:
                raise AcceptanceStageError("cleanup", cleanup_error) from cleanup_error
            print(
                f"project_drive_runtime_cleanup_error={type(cleanup_error).__name__}:"
                f"{cleanup_error}",
                flush=True,
            )

    if primary_error is not None:
        raise primary_error

    print("project_drive_runtime_acceptance=PASS", flush=True)


def main() -> int:
    try:
        asyncio.run(run_acceptance())
    except AcceptanceStageError as exc:
        print(
            f"project_drive_runtime_acceptance=FAIL stage={exc.stage} "
            f"error={type(exc.cause).__name__}:{exc.cause}",
            flush=True,
        )
        return STAGE_EXIT_CODES[exc.stage]
    except BaseException as exc:
        print(
            f"project_drive_runtime_acceptance=FAIL stage=unknown "
            f"error={type(exc).__name__}:{exc}",
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
