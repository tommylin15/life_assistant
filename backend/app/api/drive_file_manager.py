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

# Only files created/opened through this app's drive.file grant are listed.
# This is deliberately NOT a full Google Drive account explorer.
from typing import Literal
from fastapi import Query, Response
from urllib.parse import quote as _urlquote


def _q_escape(value: str) -> str:
    """Escape Drive API query literal for a user-provided search string."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _file_id(value: str) -> str:
    # Google file IDs can use '-' and '_', but never slashes or URL paths.
    if not value or len(value) > 255 or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in value
    ):
        raise HTTPException(422, "Invalid Drive file identifier")
    return value


def _file_list_payload(payload: dict) -> dict:
    if not isinstance(payload, dict) or not isinstance(payload.get("files"), list):
        raise HTTPException(502, "Google Drive file list unavailable")
    files = []
    for raw in payload["files"]:
        if not isinstance(raw, dict) or not raw.get("id") or not raw.get("name"):
            continue
        files.append({
            "id": raw["id"],
            "name": raw["name"],
            "mime_type": raw.get("mimeType"),
            "web_view_link": raw.get("webViewLink"),
            "modified_at": raw.get("modifiedTime"),
            "parents": raw.get("parents") or [],
            "can_edit": (raw.get("capabilities") or {}).get("canEdit") == True,
            "size": raw.get("size"),
            "is_folder": raw.get("mimeType") == "application/vnd.google-apps.folder",
        })
    return {
        "files": files,
        "next_page_token": payload.get("nextPageToken"),
        "incomplete_search": payload.get("incompleteSearch") == True,
        "visibility": "app_authorized_only",
    }


async def _authorized_folder(db: AsyncSession, sub: str, folder_id: str) -> str:
    folder_id = _file_id(folder_id)
    metadata = await get_drive_file_metadata(db, sub, folder_id)
    if metadata.mime_type != "application/vnd.google-apps.folder":
        raise HTTPException(422, "Selected Drive destination is not a folder")
    return folder_id


@router.get("/files")
async def list_authorized_drive_files(
    response: Response,
    folder_id: str | None = Query(default=None, max_length=255),
    q: str | None = Query(default=None, max_length=120),
    page_token: str | None = Query(default=None, max_length=2048),
    page_size: int = Query(default=50, ge=1, le=100),
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    where = ["trashed = false"]
    # A folder query is explicitly verified against the same user's OAuth.
    # With no folder selection, show all app-authorized files so the user can
    # navigate even if Drive root itself was never individually Picker-opened.
    if folder_id:
        await _authorized_folder(db, user["sub"], folder_id)
        where.append(f"'{_q_escape(folder_id)}' in parents")
    if q and q.strip():
        where.append(f"name contains '{_q_escape(q.strip())}'")
    params = {
        "q": " and ".join(where),
        "fields": "nextPageToken,incompleteSearch,files(id,name,mimeType,webViewLink,modifiedTime,parents,capabilities(canEdit),size)",
        "pageSize": str(page_size), "orderBy": "folder,name_natural",
        "spaces": "drive", "corpora": "user",
    }
    if page_token:
        params["pageToken"] = page_token
    result = await _request_google(
        db, user["sub"], SERVICE_SCOPES["drive"][0], "GET",
        "https://www.googleapis.com/drive/v3/files",
        params=params, preserve_transaction=True,
    )
    return _file_list_payload(result.json())


class DriveCreateFolder(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(min_length=1, max_length=200)
    parent_id: str | None = Field(default=None, max_length=255)

    @field_validator("name")
    @classmethod
    def trim_name(cls, value: str) -> str:
        value = value.strip()
        if not value or value in {".", ".."} or "/" in value or "\\" in value:
            raise ValueError("Invalid Drive folder name")
        return value


@router.post("/folders", status_code=201)
async def create_authorized_drive_folder(
    body: DriveCreateFolder,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    payload: dict = {
        "name": body.name, "mimeType": "application/vnd.google-apps.folder",
    }
    if body.parent_id:
        payload["parents"] = [
            await _authorized_folder(db, user["sub"], body.parent_id)
        ]
    google = await _request_google(
        db, user["sub"], SERVICE_SCOPES["drive"][0], "POST",
        "https://www.googleapis.com/drive/v3/files",
        params={"fields": "id,name,mimeType,parents"},
        json=payload, preserve_transaction=True,
    )
    item = google.json()
    if not isinstance(item, dict) or not item.get("id") or item.get("name") != body.name:
        raise HTTPException(502, "Drive folder creation readback is incomplete")
    remote = await get_drive_file_metadata(db, user["sub"], str(item["id"]))
    if remote.mime_type != "application/vnd.google-apps.folder" or remote.name != body.name:
        raise HTTPException(502, "Drive folder creation verification failed")
    return {"id": remote.id, "name": remote.name, "parent_id": body.parent_id,
            "visibility": "app_authorized_only"}


class DriveMoveDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    destination_folder_id: str = Field(min_length=1, max_length=255)
    expected_modified_at: datetime

    @field_validator("expected_modified_at")
    @classmethod
    def required_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("Drive version must have a timezone")
        return value


@router.post("/documents/{document_id}/move")
async def move_registered_drive_document(
    document_id: str,
    body: DriveMoveDocument,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    document = await get_document(db, user["sub"], document_id)
    destination = await _authorized_folder(db, user["sub"], body.destination_folder_id)
    source = await _request_google(
        db, user["sub"], SERVICE_SCOPES["drive"][0], "GET",
        FILE_URL.format(file_id=_urlquote(document.google_file_id, safe="")),
        params={"fields": "id,mimeType,parents,modifiedTime"},
        preserve_transaction=True,
    )
    remote = source.json()
    if not isinstance(remote, dict) or remote.get("id") != document.google_file_id:
        raise HTTPException(502, "Drive source file readback failed")
    try:
        stamp = datetime.fromisoformat(str(remote.get("modifiedTime")).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        raise HTTPException(502, "Drive file revision is unavailable")
    if not _same_instant(stamp, body.expected_modified_at):
        raise HTTPException(409, "Drive file changed; reload before moving")
    parents = remote.get("parents") or []
    if not isinstance(parents, list) or len(parents) != 1:
        raise HTTPException(409, "Drive file parent is ambiguous; cannot move safely")
    if destination == parents[0]:
        return {"id": document.id, "destination_folder_id": destination, "unchanged": True}
    params = {
        "addParents": destination,
        "removeParents": _file_id(str(parents[0])),
        "fields": "id,parents,modifiedTime",
    }
    result = await _request_google(
        db, user["sub"], SERVICE_SCOPES["drive"][0], "PATCH",
        FILE_URL.format(file_id=_urlquote(document.google_file_id, safe="")),
        params=params, json={}, preserve_transaction=True,
    )
    if result.json().get("id") != document.google_file_id:
        raise HTTPException(502, "Drive move response could not be confirmed")
    verify = await _request_google(
        db, user["sub"], SERVICE_SCOPES["drive"][0], "GET",
        FILE_URL.format(file_id=_urlquote(document.google_file_id, safe="")),
        params={"fields": "id,parents,modifiedTime"}, preserve_transaction=True,
    )
    final = verify.json()
    if (final.get("id") != document.google_file_id
            or destination not in (final.get("parents") or [])
            or parents[0] in (final.get("parents") or [])):
        raise HTTPException(502, "Drive move readback mismatch; inspect source")
    document.modified_at = datetime.fromisoformat(
        str(final["modifiedTime"]).replace("Z", "+00:00"))
    await db.commit()
    return {"id": document.id, "destination_folder_id": destination,
            "unchanged": False}

# Preview is ephemeral and never copied to Life PostgreSQL or Gemini.
_ALLOWED_TEXT_PREVIEW_MIME = frozenset({
    "text/plain", "text/markdown", "text/csv", "application/json",
})
_MAX_PREVIEW_BYTES = 65536


@router.get("/files/{file_id}/text-preview")
async def preview_authorized_drive_text(
    file_id: str,
    response: Response,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store"
    file_id = _file_id(file_id)
    metadata = await _request_google(
        db, user["sub"], SERVICE_SCOPES["drive"][0], "GET",
        FILE_URL.format(file_id=_urlquote(file_id, safe="")),
        params={"fields": "id,name,mimeType,size,modifiedTime"},
        preserve_transaction=True,
    )
    source = metadata.json()
    if not isinstance(source, dict) or source.get("id") != file_id:
        raise HTTPException(502, "Drive metadata mismatch")
    mime = str(source.get("mimeType") or "")
    if mime not in _ALLOWED_TEXT_PREVIEW_MIME:
        raise HTTPException(415, "This Drive file type opens in Google's viewer")
    try:
        size = int(source["size"])
    except (KeyError, ValueError, TypeError):
        raise HTTPException(409, "Drive file size unavailable; use Google viewer")
    if size > _MAX_PREVIEW_BYTES:
        raise HTTPException(413, "File too large for safe inline preview")
    content = await _request_google(
        db, user["sub"], SERVICE_SCOPES["drive"][0], "GET",
        FILE_URL.format(file_id=_urlquote(file_id, safe="")),
        params={"alt": "media"}, preserve_transaction=True,
    )
    raw = content.content
    if len(raw) > _MAX_PREVIEW_BYTES:
        raise HTTPException(413, "Inline preview exceeds limit")
    try:
        decoded = raw.decode("utf-8")
    except UnicodeDecodeError:
        raise HTTPException(415, "This file cannot be safely previewed as UTF-8")
    return {"id": file_id, "name": source.get("name"), "mime_type": mime,
            "text": decoded, "modified_at": source.get("modifiedTime"),
            "truncated": False}
