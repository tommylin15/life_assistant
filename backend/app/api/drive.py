import os

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.config import settings
from app.db.session import get_db
from app.models.drive import DriveDocument, DriveWorkspace
from app.models.drive_schemas import (
    DriveDocumentListOut,
    DriveDocumentOut,
    DriveDocumentRegister,
    DriveDocumentRegisterOut,
    DriveProjectLinksCreate,
    DriveProjectLinksOut,
    DriveWorkspaceCreate,
    DriveWorkspaceOut,
    DriveWorkspaceUpdate,
    PickerConfigOut,
)
from app.services import drive_documents
from app.services.execution_log import fail_execution
from app.services.google_oauth import SERVICE_SCOPES
from app.services.idempotency import (
    ACTION_ID_HEADER,
    commit_reserved_execution,
    replay_entity,
    reserve_execution,
)

router = APIRouter(prefix="/drive", tags=["drive"])


@router.get("/workspaces", response_model=list[DriveWorkspaceOut])
async def list_drive_workspaces(
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await drive_documents.list_workspaces(db, user["sub"])


@router.post("/workspaces", response_model=DriveWorkspaceOut, status_code=201)
async def create_drive_workspace(
    body: DriveWorkspaceCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    action_id: str | None = Header(default=None, alias=ACTION_ID_HEADER),
):
    reservation = await reserve_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.workspace.create",
        action_id=action_id,
        request_payload=body.model_dump(mode="json"),
        provider="internal",
        entity_type="drive_workspace",
        summary="Create Drive workspace",
    )
    if reservation.is_replay:
        return await replay_entity(db, reservation, DriveWorkspace)

    try:
        workspace, created = await drive_documents.create_workspace_row(
            db,
            user["sub"],
            body.google_folder_id,
            body.name,
        )
    except Exception as exc:
        await fail_execution(
            db,
            reservation.execution,
            exc,
            summary="Drive workspace create failed",
        )
        raise

    await commit_reserved_execution(
        db,
        reservation,
        result="created" if created else "existing",
        entity_type="drive_workspace",
        entity_id=workspace.id,
        summary="Drive workspace created" if created else "Drive workspace already registered",
        failure_summary="Drive workspace create failed",
        refresh_entity=workspace,
    )
    return workspace


@router.patch("/workspaces/{workspace_id}", response_model=DriveWorkspaceOut)
async def update_drive_workspace(
    workspace_id: str,
    body: DriveWorkspaceUpdate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    action_id: str | None = Header(default=None, alias=ACTION_ID_HEADER),
):
    reservation = await reserve_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.workspace.update",
        action_id=action_id,
        request_payload={
            "workspace_id": workspace_id,
            **body.model_dump(mode="json", exclude_unset=True),
        },
        provider="internal",
        entity_type="drive_workspace",
        entity_id=workspace_id,
        summary="Update Drive workspace",
    )
    if reservation.is_replay:
        return await replay_entity(db, reservation, DriveWorkspace)

    try:
        workspace = await drive_documents.get_workspace(db, user["sub"], workspace_id)
        workspace = await drive_documents.update_workspace_row(
            db,
            workspace,
            **body.model_dump(exclude_unset=True),
        )
    except Exception as exc:
        await fail_execution(
            db,
            reservation.execution,
            exc,
            summary="Drive workspace update failed",
        )
        raise

    await commit_reserved_execution(
        db,
        reservation,
        result="updated",
        entity_type="drive_workspace",
        entity_id=workspace.id,
        summary="Drive workspace updated",
        failure_summary="Drive workspace update failed",
        refresh_entity=workspace,
    )
    return workspace


@router.delete("/workspaces/{workspace_id}", status_code=204)
async def delete_drive_workspace(
    workspace_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    action_id: str | None = Header(default=None, alias=ACTION_ID_HEADER),
):
    reservation = await reserve_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.workspace.delete",
        action_id=action_id,
        request_payload={"workspace_id": workspace_id},
        provider="internal",
        entity_type="drive_workspace",
        entity_id=workspace_id,
        summary="Delete Drive workspace metadata",
    )
    if reservation.is_replay:
        return Response(status_code=204)

    try:
        workspace = await drive_documents.get_workspace(db, user["sub"], workspace_id)
        await db.delete(workspace)
    except Exception as exc:
        await fail_execution(
            db,
            reservation.execution,
            exc,
            summary="Drive workspace delete failed",
        )
        raise

    await commit_reserved_execution(
        db,
        reservation,
        result="deleted",
        entity_type="drive_workspace",
        entity_id=workspace_id,
        summary="Drive workspace metadata deleted",
        failure_summary="Drive workspace delete failed",
    )
    return Response(status_code=204)


@router.get("/picker-config", response_model=PickerConfigOut)
async def get_picker_config(
    response: Response,
    user: dict = Depends(current_user),
):
    del user
    client_id = settings.google_client_id.strip()
    developer_key = os.environ.get("GOOGLE_PICKER_DEVELOPER_KEY", "").strip()
    app_id = os.environ.get("GOOGLE_PICKER_APP_ID", "").strip()
    if not client_id or not developer_key or not app_id:
        raise HTTPException(503, "Google Picker is not configured")

    response.headers["Cache-Control"] = "no-store"
    return PickerConfigOut(
        client_id=client_id,
        developer_key=developer_key,
        app_id=app_id,
        scope=SERVICE_SCOPES["drive"][0],
    )


@router.post(
    "/documents/register",
    response_model=DriveDocumentRegisterOut,
    status_code=201,
)
async def register_drive_documents(
    body: DriveDocumentRegister,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    action_id: str | None = Header(default=None, alias=ACTION_ID_HEADER),
):
    payload = body.model_dump(mode="json")
    reservation = await reserve_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.documents.register",
        action_id=action_id,
        request_payload=payload,
        provider="google",
        entity_type="drive_document",
        summary="Register explicitly selected Drive documents",
    )
    if reservation.is_replay:
        documents = await drive_documents.get_registered_documents_by_google_ids(
            db,
            user["sub"],
            body.google_file_ids,
        )
        return DriveDocumentRegisterOut(documents=documents, returned=len(documents))

    try:
        documents = await drive_documents.register_documents(
            db,
            user["sub"],
            body.google_file_ids,
            body.workspace_id,
        )
    except Exception as exc:
        await fail_execution(
            db,
            reservation.execution,
            exc,
            summary="Drive document registration failed",
        )
        raise

    await commit_reserved_execution(
        db,
        reservation,
        result="registered",
        entity_type="drive_document",
        summary=f"Registered {len(documents)} Drive document(s)",
        failure_summary="Drive document registration failed",
    )
    return DriveDocumentRegisterOut(documents=documents, returned=len(documents))


@router.get("/documents", response_model=DriveDocumentListOut)
async def list_drive_documents(
    q: str | None = Query(default=None, max_length=200),
    workspace_id: str | None = Query(default=None, max_length=36),
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    documents = await drive_documents.list_documents(
        db,
        user["sub"],
        q=q,
        workspace_id=workspace_id,
    )
    return DriveDocumentListOut(documents=documents, returned=len(documents))


@router.get("/project-documents", response_model=DriveDocumentListOut)
async def list_drive_project_documents(
    project_id: str = Query(min_length=1, max_length=36),
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    documents = await drive_documents.list_project_documents(
        db,
        user["sub"],
        project_id,
    )
    return DriveDocumentListOut(documents=documents, returned=len(documents))


@router.post("/documents/{document_id}/projects", response_model=DriveProjectLinksOut)
async def attach_drive_document_projects(
    document_id: str,
    body: DriveProjectLinksCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    action_id: str | None = Header(default=None, alias=ACTION_ID_HEADER),
):
    payload = {
        "document_id": document_id,
        "project_ids": body.project_ids,
    }
    reservation = await reserve_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.document.projects.attach",
        action_id=action_id,
        request_payload=payload,
        provider="internal",
        entity_type="drive_document",
        entity_id=document_id,
        summary="Attach Drive document to Projects",
    )
    if reservation.is_replay:
        return DriveProjectLinksOut(
            project_ids=body.project_ids,
            returned=len(body.project_ids),
        )

    try:
        project_ids = await drive_documents.attach_document_projects(
            db,
            user["sub"],
            document_id,
            body.project_ids,
        )
    except Exception as exc:
        await fail_execution(
            db,
            reservation.execution,
            exc,
            summary="Drive document Project attachment failed",
        )
        raise

    await commit_reserved_execution(
        db,
        reservation,
        result="attached",
        entity_type="drive_document",
        entity_id=document_id,
        summary=f"Attached Drive document to {len(project_ids)} Project(s)",
        failure_summary="Drive document Project attachment failed",
    )
    return DriveProjectLinksOut(project_ids=project_ids, returned=len(project_ids))


@router.delete("/documents/{document_id}/projects/{project_id}", status_code=204)
async def detach_drive_document_project(
    document_id: str,
    project_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    action_id: str | None = Header(default=None, alias=ACTION_ID_HEADER),
):
    payload = {
        "document_id": document_id,
        "project_id": project_id,
    }
    reservation = await reserve_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.document.project.detach",
        action_id=action_id,
        request_payload=payload,
        provider="internal",
        entity_type="drive_document",
        entity_id=document_id,
        summary="Detach Drive document from Project",
    )
    if reservation.is_replay:
        return Response(status_code=204)

    try:
        removed = await drive_documents.detach_document_project(
            db,
            user["sub"],
            document_id,
            project_id,
        )
    except Exception as exc:
        await fail_execution(
            db,
            reservation.execution,
            exc,
            summary="Drive document Project detach failed",
        )
        raise

    await commit_reserved_execution(
        db,
        reservation,
        result="detached" if removed else "already_absent",
        entity_type="drive_document",
        entity_id=document_id,
        summary=(
            "Drive document detached from Project"
            if removed
            else "Drive document Project relation already absent"
        ),
        failure_summary="Drive document Project detach failed",
    )
    return Response(status_code=204)


@router.post("/documents/{document_id}/refresh", response_model=DriveDocumentOut)
async def refresh_drive_document(
    document_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
    action_id: str | None = Header(default=None, alias=ACTION_ID_HEADER),
):
    reservation = await reserve_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.document.refresh",
        action_id=action_id,
        request_payload={"document_id": document_id},
        provider="google",
        entity_type="drive_document",
        entity_id=document_id,
        summary="Refresh Drive document metadata",
    )
    if reservation.is_replay:
        return await replay_entity(db, reservation, DriveDocument)

    try:
        document = await drive_documents.refresh_document(
            db,
            user["sub"],
            document_id,
        )
    except Exception as exc:
        await fail_execution(
            db,
            reservation.execution,
            exc,
            summary="Drive document refresh failed",
        )
        raise

    await commit_reserved_execution(
        db,
        reservation,
        result="refreshed",
        entity_type="drive_document",
        entity_id=document.id,
        summary="Drive document metadata refreshed",
        failure_summary="Drive document refresh failed",
        refresh_entity=document,
    )
    return document
