from dataclasses import dataclass
from datetime import datetime
from urllib.parse import quote

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.google_api import request_google
from app.services.google_oauth import SERVICE_SCOPES

DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"
GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"
GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
GOOGLE_SHEET_MIME = "application/vnd.google-apps.spreadsheet"
GOOGLE_SLIDE_MIME = "application/vnd.google-apps.presentation"
MAX_TEXT_CHARS = 12000


@dataclass(frozen=True)
class DriveFileMetadata:
    id: str
    name: str
    mime_type: str
    web_view_link: str | None
    modified_at: datetime | None
    parents: tuple[str, ...]


@dataclass(frozen=True)
class DriveTextResult:
    supported: bool
    text: str | None
    source_mime_type: str


def _parse_google_datetime(value: object) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


async def get_drive_file_metadata(
    db: AsyncSession,
    user_sub: str,
    google_file_id: str,
) -> DriveFileMetadata:
    response = await request_google(
        db,
        user_sub,
        SERVICE_SCOPES["drive"][0],
        "GET",
        f"{DRIVE_FILES_URL}/{quote(google_file_id, safe='')}",
        params={"fields": "id,name,mimeType,webViewLink,modifiedTime,parents"},
    )
    payload = response.json()
    return DriveFileMetadata(
        id=str(payload.get("id") or google_file_id),
        name=str(payload.get("name") or "").strip(),
        mime_type=str(payload.get("mimeType") or "").strip(),
        web_view_link=(str(payload.get("webViewLink")) if payload.get("webViewLink") else None),
        modified_at=_parse_google_datetime(payload.get("modifiedTime")),
        parents=tuple(str(item) for item in (payload.get("parents") or []) if item),
    )


def _export_mime_type(source_mime_type: str) -> str | None:
    return {
        GOOGLE_DOC_MIME: "text/plain",
        GOOGLE_SHEET_MIME: "text/csv",
        GOOGLE_SLIDE_MIME: "text/plain",
    }.get(source_mime_type)


def _stored_text_supported(source_mime_type: str) -> bool:
    return source_mime_type.startswith("text/") or source_mime_type in {
        "application/json",
        "application/xml",
        "application/yaml",
        "application/x-yaml",
    }


async def read_drive_text(
    db: AsyncSession,
    user_sub: str,
    google_file_id: str,
    source_mime_type: str,
) -> DriveTextResult:
    export_mime = _export_mime_type(source_mime_type)
    if export_mime:
        response = await request_google(
            db,
            user_sub,
            SERVICE_SCOPES["drive"][0],
            "GET",
            f"{DRIVE_FILES_URL}/{quote(google_file_id, safe='')}/export",
            params={"mimeType": export_mime},
        )
        return DriveTextResult(
            supported=True,
            text=response.text[:MAX_TEXT_CHARS],
            source_mime_type=source_mime_type,
        )

    if _stored_text_supported(source_mime_type):
        response = await request_google(
            db,
            user_sub,
            SERVICE_SCOPES["drive"][0],
            "GET",
            f"{DRIVE_FILES_URL}/{quote(google_file_id, safe='')}",
            params={"alt": "media"},
        )
        return DriveTextResult(
            supported=True,
            text=response.text[:MAX_TEXT_CHARS],
            source_mime_type=source_mime_type,
        )

    return DriveTextResult(
        supported=False,
        text=None,
        source_mime_type=source_mime_type,
    )
