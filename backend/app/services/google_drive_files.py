from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.google_oauth import SERVICE_SCOPES, get_access_token

DRIVE_FILE_URL = "https://www.googleapis.com/drive/v3/files/{file_id}"
DRIVE_EXPORT_URL = "https://www.googleapis.com/drive/v3/files/{file_id}/export"
DRIVE_METADATA_FIELDS = "id,name,mimeType,webViewLink,modifiedTime"

_GOOGLE_EXPORT_MIME_TYPES = {
    "application/vnd.google-apps.document": "text/plain",
    "application/vnd.google-apps.presentation": "text/plain",
    "application/vnd.google-apps.spreadsheet": "text/csv",
}
_DIRECT_TEXT_MIME_TYPES = {
    "application/json",
    "application/xml",
    "application/csv",
    "application/javascript",
}


@dataclass(frozen=True, slots=True)
class DriveFileMetadata:
    id: str
    name: str
    mime_type: str
    web_view_link: str | None
    modified_at: datetime | None


@dataclass(frozen=True, slots=True)
class DriveTextResult:
    supported: bool
    text: str | None
    source_mime_type: str


def _parse_modified_at(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(502, "Google Drive returned invalid file metadata") from exc


async def _request_get(
    db: AsyncSession,
    user_sub: str,
    url: str,
    *,
    params: dict[str, str],
    error_label: str,
) -> httpx.Response:
    scope = SERVICE_SCOPES["drive"][0]
    token = await get_access_token(db, user_sub, scope)

    async def request(access_token: str) -> httpx.Response:
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                return await client.get(
                    url,
                    headers={"Authorization": f"Bearer {access_token}"},
                    params=params,
                )
        except httpx.HTTPError as exc:
            raise HTTPException(503, "Google Drive API unavailable") from exc

    response = await request(token)
    if response.status_code == 401:
        token = await get_access_token(
            db,
            user_sub,
            scope,
            force_refresh=True,
        )
        response = await request(token)

    if response.status_code in {401, 403}:
        raise HTTPException(
            409,
            "Google reauthorization or Drive file permission is required",
        )
    if response.status_code == 404:
        raise HTTPException(404, "Google Drive file not found or not authorized")
    if response.status_code >= 400:
        raise HTTPException(502, f"Google Drive {error_label} request failed")
    return response


async def _request_metadata(
    db: AsyncSession,
    user_sub: str,
    google_file_id: str,
) -> httpx.Response:
    url = DRIVE_FILE_URL.format(file_id=quote(google_file_id, safe=""))
    return await _request_get(
        db,
        user_sub,
        url,
        params={"fields": DRIVE_METADATA_FIELDS},
        error_label="metadata",
    )


async def get_drive_file_metadata(
    db: AsyncSession,
    user_sub: str,
    google_file_id: str,
) -> DriveFileMetadata:
    response = await _request_metadata(db, user_sub, google_file_id)
    payload = response.json()
    if not isinstance(payload, dict):
        raise HTTPException(502, "Google Drive returned invalid file metadata")

    file_id = str(payload.get("id") or "").strip()
    name = str(payload.get("name") or "").strip()
    mime_type = str(payload.get("mimeType") or "").strip()
    if file_id != google_file_id or not name or not mime_type:
        raise HTTPException(502, "Google Drive returned incomplete file metadata")

    web_view_link = str(payload.get("webViewLink") or "").strip() or None
    return DriveFileMetadata(
        id=file_id,
        name=name,
        mime_type=mime_type,
        web_view_link=web_view_link,
        modified_at=_parse_modified_at(payload.get("modifiedTime")),
    )


async def read_drive_text(
    db: AsyncSession,
    user_sub: str,
    google_file_id: str,
) -> DriveTextResult:
    metadata = await get_drive_file_metadata(db, user_sub, google_file_id)
    source_mime_type = metadata.mime_type
    export_mime = _GOOGLE_EXPORT_MIME_TYPES.get(source_mime_type)

    if export_mime is not None:
        url = DRIVE_EXPORT_URL.format(file_id=quote(google_file_id, safe=""))
        response = await _request_get(
            db,
            user_sub,
            url,
            params={"mimeType": export_mime},
            error_label="content export",
        )
        return DriveTextResult(
            supported=True,
            text=response.text,
            source_mime_type=source_mime_type,
        )

    if source_mime_type.startswith("text/") or source_mime_type in _DIRECT_TEXT_MIME_TYPES:
        url = DRIVE_FILE_URL.format(file_id=quote(google_file_id, safe=""))
        response = await _request_get(
            db,
            user_sub,
            url,
            params={"alt": "media"},
            error_label="content download",
        )
        return DriveTextResult(
            supported=True,
            text=response.text,
            source_mime_type=source_mime_type,
        )

    return DriveTextResult(
        supported=False,
        text=None,
        source_mime_type=source_mime_type,
    )
