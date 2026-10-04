import uuid

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.drive import (
    DriveDocument,
    DriveWorkspace,
    DriveWorkspaceDocument,
    NoteDriveDocument,
    ProjectDriveDocument,
)
from app.models.migration_support import EntityTag, Tag
from app.models.note import Note
from app.models.project import Project
from app.services.google_drive_files import get_drive_file_metadata, read_drive_text


async def get_workspace(
    db: AsyncSession,
    user_sub: str,
    workspace_id: str,
) -> DriveWorkspace:
    result = await db.execute(
        select(DriveWorkspace).where(
            DriveWorkspace.id == workspace_id,
            DriveWorkspace.user_sub == user_sub,
        )
    )
    workspace = result.scalar_one_or_none()
    if workspace is None:
        raise HTTPException(404, "Drive workspace not found")
    return workspace


async def list_workspaces(
    db: AsyncSession,
    user_sub: str,
) -> list[DriveWorkspace]:
    result = await db.execute(
        select(DriveWorkspace)
        .where(DriveWorkspace.user_sub == user_sub)
        .order_by(DriveWorkspace.created_at.asc())
    )
    return list(result.scalars().all())


async def find_workspace_by_google_folder(
    db: AsyncSession,
    user_sub: str,
    google_folder_id: str,
) -> DriveWorkspace | None:
    result = await db.execute(
        select(DriveWorkspace).where(
            DriveWorkspace.user_sub == user_sub,
            DriveWorkspace.google_folder_id == google_folder_id,
        )
    )
    return result.scalar_one_or_none()


async def create_workspace_row(
    db: AsyncSession,
    user_sub: str,
    google_folder_id: str,
    name: str,
) -> tuple[DriveWorkspace, bool]:
    existing = await find_workspace_by_google_folder(
        db,
        user_sub,
        google_folder_id,
    )
    if existing is not None:
        return existing, False
    workspace = DriveWorkspace(
        id=str(uuid.uuid4()),
        user_sub=user_sub,
        google_folder_id=google_folder_id,
        name=name,
    )
    db.add(workspace)
    return workspace, True


async def update_workspace_row(
    db: AsyncSession,
    workspace: DriveWorkspace,
    *,
    name: str | None = None,
    is_enabled: bool | None = None,
    is_default: bool | None = None,
) -> DriveWorkspace:
    if is_default is True:
        await db.execute(
            update(DriveWorkspace)
            .where(
                DriveWorkspace.user_sub == workspace.user_sub,
                DriveWorkspace.id != workspace.id,
            )
            .values(is_default=False)
        )
    if name is not None:
        workspace.name = name
    if is_enabled is not None:
        workspace.is_enabled = is_enabled
    if is_default is not None:
        workspace.is_default = is_default
    return workspace


async def _find_document_by_google_file(
    db: AsyncSession,
    user_sub: str,
    google_file_id: str,
) -> DriveDocument | None:
    result = await db.execute(
        select(DriveDocument).where(
            DriveDocument.user_sub == user_sub,
            DriveDocument.google_file_id == google_file_id,
        )
    )
    return result.scalar_one_or_none()


async def get_document(
    db: AsyncSession,
    user_sub: str,
    document_id: str,
) -> DriveDocument:
    result = await db.execute(
        select(DriveDocument).where(
            DriveDocument.id == document_id,
            DriveDocument.user_sub == user_sub,
        )
    )
    document = result.scalar_one_or_none()
    if document is None:
        raise HTTPException(404, "Drive document not found")
    return document


async def get_registered_documents_by_google_ids(
    db: AsyncSession,
    user_sub: str,
    google_file_ids: list[str],
) -> list[DriveDocument]:
    result = await db.execute(
        select(DriveDocument)
        .where(
            DriveDocument.user_sub == user_sub,
            DriveDocument.google_file_id.in_(google_file_ids),
        )
        .order_by(DriveDocument.created_at.asc())
    )
    documents_by_id = {
        document.google_file_id: document for document in result.scalars().all()
    }
    return [
        documents_by_id[file_id]
        for file_id in google_file_ids
        if file_id in documents_by_id
    ]


async def _ensure_workspace_document_link(
    db: AsyncSession,
    workspace_id: str,
    drive_document_id: str,
) -> None:
    result = await db.execute(
        select(DriveWorkspaceDocument).where(
            DriveWorkspaceDocument.workspace_id == workspace_id,
            DriveWorkspaceDocument.drive_document_id == drive_document_id,
        )
    )
    if result.scalar_one_or_none() is None:
        db.add(
            DriveWorkspaceDocument(
                workspace_id=workspace_id,
                drive_document_id=drive_document_id,
            )
        )


async def register_documents(
    db: AsyncSession,
    user_sub: str,
    google_file_ids: list[str],
    workspace_id: str | None = None,
) -> list[DriveDocument]:
    if workspace_id is not None:
        await get_workspace(db, user_sub, workspace_id)

    documents: list[DriveDocument] = []
    for google_file_id in google_file_ids:
        metadata = await get_drive_file_metadata(db, user_sub, google_file_id)
        document = await _find_document_by_google_file(
            db,
            user_sub,
            google_file_id,
        )
        if document is None:
            document = DriveDocument(
                id=str(uuid.uuid4()),
                user_sub=user_sub,
                google_file_id=metadata.id,
                name=metadata.name,
                mime_type=metadata.mime_type,
                web_view_link=metadata.web_view_link,
                modified_at=metadata.modified_at,
            )
            db.add(document)
        else:
            document.name = metadata.name
            document.mime_type = metadata.mime_type
            document.web_view_link = metadata.web_view_link
            document.modified_at = metadata.modified_at

        if workspace_id is not None:
            await _ensure_workspace_document_link(
                db,
                workspace_id,
                document.id,
            )
        documents.append(document)
    return documents


async def list_documents(
    db: AsyncSession,
    user_sub: str,
    *,
    q: str | None = None,
    workspace_id: str | None = None,
) -> list[DriveDocument]:
    statement = select(DriveDocument).where(DriveDocument.user_sub == user_sub)
    if workspace_id is not None:
        await get_workspace(db, user_sub, workspace_id)
        statement = statement.join(
            DriveWorkspaceDocument,
            DriveWorkspaceDocument.drive_document_id == DriveDocument.id,
        ).where(DriveWorkspaceDocument.workspace_id == workspace_id)
    if q:
        statement = statement.where(DriveDocument.name.ilike(f"%{q.strip()}%"))
    statement = statement.order_by(DriveDocument.updated_at.desc())
    result = await db.execute(statement)
    return list(result.scalars().all())


async def refresh_document(
    db: AsyncSession,
    user_sub: str,
    document_id: str,
) -> DriveDocument:
    document = await get_document(db, user_sub, document_id)
    metadata = await get_drive_file_metadata(
        db,
        user_sub,
        document.google_file_id,
    )
    document.name = metadata.name
    document.mime_type = metadata.mime_type
    document.web_view_link = metadata.web_view_link
    document.modified_at = metadata.modified_at
    return document


async def _require_project(db: AsyncSession, project_id: str) -> Project:
    project = await db.get(Project, project_id)
    if project is None:
        raise HTTPException(404, "Project not found")
    return project


async def _require_note(db: AsyncSession, note_id: str) -> Note:
    note = await db.get(Note, note_id)
    if note is None:
        raise HTTPException(404, "Note not found")
    return note


async def _apply_note_tags(
    db: AsyncSession,
    note_id: str,
    tag_names: list[str],
) -> None:
    for name in tag_names:
        tag = (
            await db.execute(
                select(Tag).where(func.lower(Tag.name) == name.casefold()).limit(1)
            )
        ).scalar_one_or_none()
        if tag is None:
            tag = Tag(id=str(uuid.uuid4()), name=name)
            db.add(tag)
            await db.flush()
        db.add(EntityTag(entity_type="note", entity_id=note_id, tag_id=tag.id))


async def import_document_to_note(
    db: AsyncSession,
    user_sub: str,
    document_id: str,
    *,
    title: str | None,
    project_id: str | None,
    tags: list[str],
) -> Note:
    document = await get_document(db, user_sub, document_id)
    if project_id is not None:
        await _require_project(db, project_id)

    snapshot = await read_drive_text(db, user_sub, document.google_file_id)
    if not snapshot.supported or snapshot.text is None:
        raise HTTPException(422, "drive_text_unavailable")

    note = Note(
        id=str(uuid.uuid4()),
        title=document.name if title is None else title,
        body=snapshot.text,
        project_id=project_id,
    )
    db.add(note)
    db.add(
        NoteDriveDocument(
            note_id=note.id,
            drive_document_id=document.id,
            relation_type="source_import",
            link_source="import",
        )
    )
    await _apply_note_tags(db, note.id, tags)
    return note


async def attach_document_note(
    db: AsyncSession,
    user_sub: str,
    document_id: str,
    note_id: str,
) -> tuple[NoteDriveDocument, bool]:
    document = await get_document(db, user_sub, document_id)
    await _require_note(db, note_id)
    relation = await db.get(
        NoteDriveDocument,
        {
            "note_id": note_id,
            "drive_document_id": document.id,
        },
    )
    if relation is not None:
        return relation, False
    relation = NoteDriveDocument(
        note_id=note_id,
        drive_document_id=document.id,
        relation_type="related",
        link_source="manual",
    )
    db.add(relation)
    return relation, True


async def detach_document_note(
    db: AsyncSession,
    user_sub: str,
    document_id: str,
    note_id: str,
) -> bool:
    document = await get_document(db, user_sub, document_id)
    relation = await db.get(
        NoteDriveDocument,
        {
            "note_id": note_id,
            "drive_document_id": document.id,
        },
    )
    if relation is None:
        return False
    if relation.relation_type == "source_import":
        raise HTTPException(409, "Drive source import relation cannot be unlinked")
    await db.delete(relation)
    return True


async def list_document_note_relations(
    db: AsyncSession,
    user_sub: str,
    document_id: str,
) -> list[tuple[Note, NoteDriveDocument]]:
    document = await get_document(db, user_sub, document_id)
    result = await db.execute(
        select(Note, NoteDriveDocument)
        .join(NoteDriveDocument, NoteDriveDocument.note_id == Note.id)
        .where(NoteDriveDocument.drive_document_id == document.id)
        .order_by(NoteDriveDocument.created_at.asc(), Note.id.asc())
    )
    return list(result.all())


async def list_note_document_relations(
    db: AsyncSession,
    user_sub: str,
    note_id: str,
) -> list[tuple[DriveDocument, NoteDriveDocument]]:
    await _require_note(db, note_id)
    result = await db.execute(
        select(DriveDocument, NoteDriveDocument)
        .join(
            NoteDriveDocument,
            NoteDriveDocument.drive_document_id == DriveDocument.id,
        )
        .where(
            NoteDriveDocument.note_id == note_id,
            DriveDocument.user_sub == user_sub,
        )
        .order_by(NoteDriveDocument.created_at.asc(), DriveDocument.id.asc())
    )
    return list(result.all())


async def list_project_documents(
    db: AsyncSession,
    user_sub: str,
    project_id: str,
) -> list[DriveDocument]:
    await _require_project(db, project_id)
    result = await db.execute(
        select(DriveDocument)
        .join(
            ProjectDriveDocument,
            ProjectDriveDocument.drive_document_id == DriveDocument.id,
        )
        .where(
            ProjectDriveDocument.project_id == project_id,
            DriveDocument.user_sub == user_sub,
        )
        .order_by(DriveDocument.updated_at.desc())
    )
    return list(result.scalars().all())


async def attach_document_projects(
    db: AsyncSession,
    user_sub: str,
    document_id: str,
    project_ids: list[str],
) -> list[str]:
    document = await get_document(db, user_sub, document_id)

    for project_id in project_ids:
        await _require_project(db, project_id)

    for project_id in project_ids:
        relation = await db.get(
            ProjectDriveDocument,
            {
                "project_id": project_id,
                "drive_document_id": document.id,
            },
        )
        if relation is None:
            db.add(
                ProjectDriveDocument(
                    project_id=project_id,
                    drive_document_id=document.id,
                )
            )
    return project_ids


async def detach_document_project(
    db: AsyncSession,
    user_sub: str,
    document_id: str,
    project_id: str,
) -> bool:
    document = await get_document(db, user_sub, document_id)
    await _require_project(db, project_id)
    relation = await db.get(
        ProjectDriveDocument,
        {
            "project_id": project_id,
            "drive_document_id": document.id,
        },
    )
    if relation is None:
        return False
    await db.delete(relation)
    return True
