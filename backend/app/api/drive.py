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
)
from app.models.drive_schemas import (
    DriveAiSettingsOut,
    DriveAiSettingsUpdate,
    DriveDocumentOut,
    DriveDocumentsRegister,
    DriveWorkspaceCreate,
    DriveWorkspaceOut,
    DriveWorkspaceUpdate,
    PickerConfigOut,
)
from app.services.drive_documents import (
    create_workspace,
    get_owned_workspace,
    refresh_document,
    register_documents,
    unregister_document,
)
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


@router.delete("/documents/{document_id}", status_code=204)
async def delete_drive_document_registration(
    document_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await unregister_document(db, user["sub"], document_id)
    return Response(status_code=204)
