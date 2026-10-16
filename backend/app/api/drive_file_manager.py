"""Owner-scoped Drive file-manager commands for Picker-authorized files.

Full-drive browsing is NOT implied by the drive.file OAuth scope.
All writes start from an existing owner-scoped DriveDocument, never a
caller-provided raw Google file ID.
"""
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.api.google_integrations import _request_google
from app.db.session import get_db
from app.models.drive_schemas import DriveDocumentOut
from app.services.drive_documents import get_document
from app.services.google_oauth import SERVICE_SCOPES
from app.services.google_drive_files import get_drive_file_metadata

router = APIRouter(prefix="/drive/manager", tags=["drive-file-manager"])
FILE_URL = "https://www.googleapis.com/drive/v3/files/{file_id}"


class DriveRenameRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=500)
    # Client MUST specify the version last shown to the user; missing
    # modifiedTime means edit stays disabled until metadata refresh works.
    expected_modified_at: datetime

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value or value in (".", "..") or "/" in value or "\\x00" in value:
            raise ValueError("Invalid Drive filename")
        return value

    @field_validator("expected_modified_at")
    @classmethod
    def timezone_required(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Drive modification time requires timezone")
        return value


def _same_instant(left: datetime | None, right: datetime) -> bool:
    return left is not None and left.astimezone(timezone.utc) == right.astimezone(timezone.utc)


@router.patch("/documents/{document_id}/rename", response_model=DriveDocumentOut)
async def rename_registered_document(
    document_id: str,
    body: DriveRenameRequest,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    # The internal ID is owner-scoped before contacting Google.
    doc = await get_document(db, user["sub"], document_id)
    current = await get_drive_file_metadata(db, user["sub"], doc.google_file_id)
    if not _same_instant(current.modified_at, body.expected_modified_at):
        raise HTTPException(409, "Drive file changed; refresh before editing")
    if current.name == body.name:
        # No remote write necessary.
        doc.name = current.name
        doc.modified_at = current.modified_at
        doc.web_view_link = current.web_view_link
        await db.commit()
        return doc
    response = await _request_google(
        db, user["sub"], SERVICE_SCOPES["drive"][0], "PATCH",
        FILE_URL.format(file_id=quote(doc.google_file_id, safe="")),
        params={"fields": "id,name,mimeType,webViewLink,modifiedTime"},
        json={"name": body.name},
        preserve_transaction=True,
    )
    result = response.json()
    if result.get("id") != doc.google_file_id or result.get("name") != body.name:
        raise HTTPException(502, "Drive rename response is inconsistent; refresh before retrying")
    # Only after Google accepted the rename, advance local display metadata.
    updated = await get_drive_file_metadata(db, user["sub"], doc.google_file_id)
    if updated.name != body.name:
        raise HTTPException(502, "Drive rename readback did not match; refresh before retrying")
    doc.name = updated.name
    doc.modified_at = updated.modified_at
    doc.mime_type = updated.mime_type
    doc.web_view_link = updated.web_view_link
    await db.commit()
    return doc
