import os

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app import config as app_config
from app.api.auth import current_user
from app.db.session import get_db
from app.models.drive import (
    DriveAiSettings,
    DriveDocument,
    DriveWorkspace,
    DriveWorkspaceDocument,
    NoteDriveDocument,
    ProjectDriveDocument,
)
from app.models.drive_schemas import (
    DriveAiSettingsOut,
    DriveAiSettingsUpdate,
    DriveDocumentOut,
    DriveDocumentsRegister,
    DriveNoteDocumentOut,
    DriveNoteImportCreate,
    DriveNoteRelationOut,
    DriveProjectDocumentOut,
    DriveProjectLinkOut,
    DriveProjectLinksCreate,
    DriveRelatedNoteOut,
    DriveWorkspaceCreate,
    DriveWorkspaceOut,
    DriveWorkspaceUpdate,
    PickerConfigOut,
)
from app.models.note import Note
from app.models.schemas import NoteOut
from app.services.drive_documents import (
    attach_document_to_projects,
    create_workspace,
    detach_document_from_project,
    get_owned_workspace,
    import_document_to_note,
    link_document_to_note,
    refresh_document,
    register_documents,
    unlink_document_from_note,
    unregister_document,
)
from app.services.execution_log import fail_execution, finish_execution, start_execution
from app.services.google_oauth import SERVICE_SCOPES

router = APIRouter(prefix="/drive", tags=["drive"])


def _picker_setting(attribute: str, env_name: str) -> str:
    value = str(getattr(app_config.settings, attribute, "") or "").strip()
    if value:
        return value
    return os.environ.get(env_name, "").strip()


@router.get("/picker-config", response_model=PickerConfigOut)
async def get_picker_config(_user: dict = Depends(current_user)) -> PickerConfigOut:
    client_id = str(app_config.settings.google_client_id or "").strip()
    developer_key = _picker_setting(
        "google_picker_developer_key", "GOOGLE_PICKER_DEVELOPER_KEY"
    )
    app_id = _picker_setting("google_picker_app_id", "GOOGLE_PICKER_APP_ID")
    if not client_id or not developer_key or not app_id:
        raise HTTPException(503, "Google Picker is not configured")
    return PickerConfigOut(
        client_id=client_id,
        developer_key=developer_key,
        app_id=app_id,
        scope=SERVICE_SCOPES["drive"][0],
    )


@router.get("/workspaces", response_model=list[DriveWorkspaceOut])
async def list_drive_workspaces(
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(DriveWorkspace)
        .where(DriveWorkspace.owner_sub == user["sub"])
        .order_by(DriveWorkspace.is_default.desc(), DriveWorkspace.created_at.asc())
    )
    return result.scalars().all()


@router.post("/workspaces", response_model=DriveWorkspaceOut, status_code=201)
async def create_drive_workspace(
    body: DriveWorkspaceCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await create_workspace(db, user["sub"], body)


@router.patch("/workspaces/{workspace_id}", response_model=DriveWorkspaceOut)
async def update_drive_workspace(
    workspace_id: str,
    body: DriveWorkspaceUpdate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    workspace = await get_owned_workspace(db, user["sub"], workspace_id)
    values = body.model_dump(exclude_unset=True)
    if values.get("is_default") is True:
        await db.execute(
            update(DriveWorkspace)
            .where(
                DriveWorkspace.owner_sub == user["sub"],
                DriveWorkspace.id != workspace.id,
            )
            .values(is_default=False)
        )
    for field, value in values.items():
        setattr(workspace, field, value)
    await db.commit()
    await db.refresh(workspace)
    return workspace


@router.delete("/workspaces/{workspace_id}", status_code=204)
async def delete_drive_workspace(
    workspace_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    workspace = await get_owned_workspace(db, user["sub"], workspace_id)
    await db.execute(
        delete(DriveWorkspaceDocument).where(
            DriveWorkspaceDocument.workspace_id == workspace.id
        )
    )
    await db.delete(workspace)
    await db.commit()
    return Response(status_code=204)


@router.get("/ai-settings", response_model=DriveAiSettingsOut)
async def get_drive_ai_settings(
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = await db.get(DriveAiSettings, user["sub"])
    if settings is None:
        return DriveAiSettingsOut()
    return settings


@router.put("/ai-settings", response_model=DriveAiSettingsOut)
async def update_drive_ai_settings(
    body: DriveAiSettingsUpdate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    settings = await db.get(DriveAiSettings, user["sub"])
    if settings is None:
        settings = DriveAiSettings(owner_sub=user["sub"])
        db.add(settings)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(settings, field, value)
    await db.commit()
    await db.refresh(settings)
    return settings


@router.get("/documents", response_model=list[DriveDocumentOut])
async def list_drive_documents(
    q: str | None = Query(default=None),
    workspace_id: str | None = Query(default=None),
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    statement = select(DriveDocument).where(
        DriveDocument.owner_sub == user["sub"]
    )
    if workspace_id:
        statement = statement.join(
            DriveWorkspaceDocument,
            DriveWorkspaceDocument.drive_document_id == DriveDocument.id,
        ).where(DriveWorkspaceDocument.workspace_id == workspace_id)
    query = (q or "").strip()
    if query:
        statement = statement.where(DriveDocument.name.ilike(f"%{query}%"))
    statement = statement.order_by(DriveDocument.updated_at.desc())
    result = await db.execute(statement)
    return result.scalars().all()


@router.post("/documents/register", response_model=list[DriveDocumentOut], status_code=201)
async def register_drive_documents(
    body: DriveDocumentsRegister,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await register_documents(
        db,
        user["sub"],
        body.google_file_ids,
        workspace_id=body.workspace_id,
    )


@router.post("/documents/{document_id}/refresh", response_model=DriveDocumentOut)
async def refresh_drive_document(
    document_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await refresh_document(db, user["sub"], document_id)


@router.get("/project-documents", response_model=list[DriveProjectDocumentOut])
async def list_project_drive_documents(
    project_id: str | None = Query(default=None),
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    statement = (
        select(ProjectDriveDocument, DriveDocument)
        .join(
            DriveDocument,
            DriveDocument.id == ProjectDriveDocument.drive_document_id,
        )
        .where(DriveDocument.owner_sub == user["sub"])
    )
    if project_id:
        statement = statement.where(ProjectDriveDocument.project_id == project_id)
    result = await db.execute(
        statement.order_by(ProjectDriveDocument.created_at.desc())
    )
    return [
        DriveProjectDocumentOut(
            project_id=relation.project_id,
            drive_document_id=document.id,
            google_file_id=document.google_file_id,
            name=document.name,
            mime_type=document.mime_type,
            web_view_link=document.web_view_link,
            provider_modified_at=document.provider_modified_at,
        )
        for relation, document in result.all()
    ]


@router.post(
    "/documents/{document_id}/projects",
    response_model=list[DriveProjectLinkOut],
)
async def attach_drive_document_to_projects(
    document_id: str,
    body: DriveProjectLinksCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.project.attach",
        provider="internal",
        entity_type="drive_document",
        entity_id=document_id,
        summary="Attach Drive document to projects",
    )
    try:
        links = await attach_document_to_projects(
            db,
            user["sub"],
            document_id,
            body.project_ids,
        )
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Drive project attach failed")
        raise
    await finish_execution(
        db,
        execution,
        result="attached",
        summary="Drive document attached to projects",
    )
    return links


@router.delete("/documents/{document_id}/projects/{project_id}", status_code=204)
async def detach_drive_document_from_project(
    document_id: str,
    project_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.project.detach",
        provider="internal",
        entity_type="drive_document",
        entity_id=document_id,
        summary="Detach Drive document from project",
    )
    try:
        await detach_document_from_project(
            db,
            user["sub"],
            document_id,
            project_id,
        )
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Drive project detach failed")
        raise
    await finish_execution(
        db,
        execution,
        result="detached",
        summary="Drive document detached from project",
    )
    return Response(status_code=204)


@router.post(
    "/documents/{document_id}/note-import",
    response_model=NoteOut,
    status_code=201,
)
async def import_drive_document_to_note(
    document_id: str,
    body: DriveNoteImportCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.note.import",
        provider="internal",
        entity_type="drive_document",
        entity_id=document_id,
        summary="Import Drive document to note",
    )
    try:
        note = await import_document_to_note(
            db,
            user["sub"],
            document_id,
            title=body.title,
            project_id=body.project_id,
            tags=body.tags,
        )
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Drive note import failed")
        raise
    await finish_execution(
        db,
        execution,
        result="imported",
        entity_id=note.id,
        summary="Drive document imported to note",
    )
    return note


@router.get(
    "/documents/{document_id}/notes",
    response_model=list[DriveRelatedNoteOut],
)
async def list_drive_document_notes(
    document_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(NoteDriveDocument, Note)
        .join(Note, Note.id == NoteDriveDocument.note_id)
        .join(DriveDocument, DriveDocument.id == NoteDriveDocument.drive_document_id)
        .where(
            NoteDriveDocument.drive_document_id == document_id,
            DriveDocument.owner_sub == user["sub"],
        )
        .order_by(NoteDriveDocument.created_at.desc())
    )
    return [
        DriveRelatedNoteOut(
            note_id=note.id,
            drive_document_id=relation.drive_document_id,
            relation_type=relation.relation_type,
            relation_origin=relation.relation_origin,
            title=note.title,
            body=note.body,
            project_id=note.project_id,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )
        for relation, note in result.all()
    ]


@router.post(
    "/documents/{document_id}/notes/{note_id}",
    response_model=DriveNoteRelationOut,
    status_code=201,
)
async def link_drive_document_to_note(
    document_id: str,
    note_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.note.link",
        provider="internal",
        entity_type="drive_document",
        entity_id=document_id,
        summary="Link Drive document to note",
    )
    try:
        relation = await link_document_to_note(
            db,
            user["sub"],
            document_id,
            note_id,
        )
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Drive note link failed")
        raise
    await finish_execution(
        db,
        execution,
        result="linked",
        summary="Drive document linked to note",
    )
    return relation


@router.delete("/documents/{document_id}/notes/{note_id}", status_code=204)
async def unlink_drive_document_from_note(
    document_id: str,
    note_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    execution = await start_execution(
        db,
        user_sub=user["sub"],
        action_type="drive.note.unlink",
        provider="internal",
        entity_type="drive_document",
        entity_id=document_id,
        summary="Unlink Drive document from note",
    )
    try:
        await unlink_document_from_note(
            db,
            user["sub"],
            document_id,
            note_id,
        )
    except Exception as exc:
        await fail_execution(db, execution, exc, summary="Drive note unlink failed")
        raise
    await finish_execution(
        db,
        execution,
        result="unlinked",
        summary="Drive document unlinked from note",
    )
    return Response(status_code=204)


@router.get("/notes/{note_id}/documents", response_model=list[DriveNoteDocumentOut])
async def list_note_drive_documents(
    note_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    note = await db.get(Note, note_id)
    if note is None:
        raise HTTPException(404, "Note not found")
    result = await db.execute(
        select(NoteDriveDocument, DriveDocument)
        .join(DriveDocument, DriveDocument.id == NoteDriveDocument.drive_document_id)
        .where(
            NoteDriveDocument.note_id == note_id,
            DriveDocument.owner_sub == user["sub"],
        )
        .order_by(NoteDriveDocument.created_at.desc())
    )
    return [
        DriveNoteDocumentOut(
            note_id=relation.note_id,
            drive_document_id=document.id,
            relation_type=relation.relation_type,
            relation_origin=relation.relation_origin,
            google_file_id=document.google_file_id,
            name=document.name,
            mime_type=document.mime_type,
            web_view_link=document.web_view_link,
            provider_modified_at=document.provider_modified_at,
        )
        for relation, document in result.all()
    ]


@router.delete("/documents/{document_id}", status_code=204)
async def delete_drive_document_registration(
    document_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await unregister_document(db, user["sub"], document_id)
    return Response(status_code=204)
