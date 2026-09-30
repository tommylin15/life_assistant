from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drive import (
    DriveDocument,
    DriveDocumentEnrichmentRun,
    DriveNoteLinkSuggestion,
    DriveWorkspace,
    DriveWorkspaceDocument,
    NoteDriveDocument,
    ProjectDriveDocument,
)
from app.models.drive_schemas import DriveWorkspaceCreate
from app.models.migration_support import EntityTag
from app.services.google_drive_files import (
    GOOGLE_FOLDER_MIME,
    get_drive_file_metadata,
)


async def get_owned_workspace(
    db: AsyncSession, owner_sub: str, workspace_id: str
) -> DriveWorkspace:
    result = await db.execute(
        select(DriveWorkspace).where(
            DriveWorkspace.id == workspace_id,
            DriveWorkspace.owner_sub == owner_sub,
        )
    )
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(404, "Drive workspace not found")
    return workspace


async def get_owned_document(
    db: AsyncSession, owner_sub: str, document_id: str
) -> DriveDocument:
    result = await db.execute(
        select(DriveDocument).where(
            DriveDocument.id == document_id,
            DriveDocument.owner_sub == owner_sub,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(404, "Drive document not found")
    return document


async def create_workspace(
    db: AsyncSession,
    owner_sub: str,
    body: DriveWorkspaceCreate,
) -> DriveWorkspace:
    metadata = await get_drive_file_metadata(db, owner_sub, body.google_folder_id)
    if metadata.mime_type != GOOGLE_FOLDER_MIME:
        raise HTTPException(422, "Selected Google Drive item is not a folder")

    existing_result = await db.execute(
        select(DriveWorkspace).where(
            DriveWorkspace.owner_sub == owner_sub,
            DriveWorkspace.google_folder_id == metadata.id,
        )
    )
    existing = existing_result.scalar_one_or_none()
    if existing is not None:
        return existing

    workspace = DriveWorkspace(
        owner_sub=owner_sub,
        google_folder_id=metadata.id,
        name=(body.name or metadata.name or "Google Drive workspace").strip(),
        web_view_link=metadata.web_view_link,
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace


async def register_documents(
    db: AsyncSession,
    owner_sub: str,
    google_file_ids: list[str],
    workspace_id: str | None = None,
) -> list[DriveDocument]:
    workspace = None
    if workspace_id is not None:
        workspace = await get_owned_workspace(db, owner_sub, workspace_id)

    documents: list[DriveDocument] = []
    seen: set[str] = set()
    for google_file_id in google_file_ids:
        if google_file_id in seen:
            continue
        seen.add(google_file_id)
        metadata = await get_drive_file_metadata(db, owner_sub, google_file_id)
        if metadata.mime_type == GOOGLE_FOLDER_MIME:
            raise HTTPException(422, "Folders must be configured as Drive workspaces")

        existing_result = await db.execute(
            select(DriveDocument).where(
                DriveDocument.owner_sub == owner_sub,
                DriveDocument.google_file_id == metadata.id,
            )
        )
        document = existing_result.scalar_one_or_none()
        now = datetime.now(timezone.utc)
        if document is None:
            document = DriveDocument(
                owner_sub=owner_sub,
                google_file_id=metadata.id,
                name=metadata.name or "Google Drive file",
                mime_type=metadata.mime_type or "application/octet-stream",
                web_view_link=metadata.web_view_link,
                provider_modified_at=metadata.modified_at,
                last_metadata_refresh_at=now,
            )
            db.add(document)
            await db.flush()
        else:
            document.name = metadata.name or document.name
            document.mime_type = metadata.mime_type or document.mime_type
            document.web_view_link = metadata.web_view_link
            document.provider_modified_at = metadata.modified_at
            document.last_metadata_refresh_at = now

        if workspace is not None:
            relation_result = await db.execute(
                select(DriveWorkspaceDocument).where(
                    DriveWorkspaceDocument.workspace_id == workspace.id,
                    DriveWorkspaceDocument.drive_document_id == document.id,
                )
            )
            if relation_result.scalar_one_or_none() is None:
                db.add(
                    DriveWorkspaceDocument(
                        workspace_id=workspace.id,
                        drive_document_id=document.id,
                    )
                )
        documents.append(document)

    await db.commit()
    for document in documents:
        await db.refresh(document)
    return documents


async def refresh_document(
    db: AsyncSession,
    owner_sub: str,
    document_id: str,
) -> DriveDocument:
    document = await get_owned_document(db, owner_sub, document_id)
    metadata = await get_drive_file_metadata(db, owner_sub, document.google_file_id)
    document.name = metadata.name or document.name
    document.mime_type = metadata.mime_type or document.mime_type
    document.web_view_link = metadata.web_view_link
    document.provider_modified_at = metadata.modified_at
    document.last_metadata_refresh_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(document)
    return document


async def unregister_document(
    db: AsyncSession,
    owner_sub: str,
    document_id: str,
) -> None:
    document = await get_owned_document(db, owner_sub, document_id)

    for model in (DriveWorkspaceDocument, ProjectDriveDocument, NoteDriveDocument):
        result = await db.execute(
            select(model.drive_document_id)
            .where(model.drive_document_id == document.id)
            .limit(1)
        )
        if result.scalar_one_or_none() is not None:
            raise HTTPException(409, "Drive document still has app relationships")

    await db.execute(
        delete(EntityTag).where(
            EntityTag.entity_type == "drive_document",
            EntityTag.entity_id == document.id,
        )
    )
    await db.execute(
        delete(DriveNoteLinkSuggestion).where(
            DriveNoteLinkSuggestion.drive_document_id == document.id
        )
    )
    await db.execute(
        delete(DriveDocumentEnrichmentRun).where(
            DriveDocumentEnrichmentRun.drive_document_id == document.id
        )
    )
    await db.delete(document)
    await db.commit()
