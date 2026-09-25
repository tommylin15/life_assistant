from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.google_integration import GoogleConnection
from app.services.google_oauth import (
    SERVICE_SCOPES,
    build_authorization_url,
    create_authorization_state,
    get_access_token,
    granted_services,
    normalize_services,
    token_key_source,
    token_storage_ready,
)

router = APIRouter(prefix="/integrations/google", tags=["google-integrations"])

CAPABILITIES = [
    {
        "name": "gmail.list_metadata",
        "version": "1.0",
        "service": "gmail",
        "required_scope": SERVICE_SCOPES["gmail"][0],
        "risk": "read",
        "confirmation": "none",
    },
    {
        "name": "calendar.list",
        "version": "1.0",
        "service": "calendar",
        "required_scope": SERVICE_SCOPES["calendar"][0],
        "risk": "read",
        "confirmation": "none",
    },
    {
        "name": "calendar.create",
        "version": "1.0",
        "service": "calendar",
        "required_scope": SERVICE_SCOPES["calendar"][0],
        "risk": "write",
        "confirmation": "explicit_user_or_policy",
    },
    {
        "name": "drive.bridge.ensure",
        "version": "1.0",
        "service": "drive",
        "required_scope": SERVICE_SCOPES["drive"][0],
        "risk": "write_limited",
        "confirmation": "explicit_user_or_policy",
    },
]

GMAIL_LIST_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
GMAIL_MESSAGE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


class CalendarEventCreate(BaseModel):
    summary: str = Field(min_length=1, max_length=500)
    start: datetime
    end: datetime
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_times(self):
        if self.start.tzinfo is None or self.end.tzinfo is None:
            raise ValueError("Calendar event times must include a timezone")
        if self.end <= self.start:
            raise ValueError("Calendar event end must be after start")
        return self


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _request_google(
    db: AsyncSession,
    user_sub: str,
    scope: str,
    method: str,
    url: str,
    **kwargs,
) -> httpx.Response:
    token = await get_access_token(db, user_sub, scope)
    headers = dict(kwargs.pop("headers", {}))
    headers.update(_auth_headers(token))
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.request(method, url, headers=headers, **kwargs)
    except httpx.HTTPError as exc:
        raise HTTPException(503, "Google API unavailable") from exc

    if response.status_code == 401:
        token = await get_access_token(db, user_sub, scope, force_refresh=True)
        headers.update(_auth_headers(token))
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.request(method, url, headers=headers, **kwargs)
        except httpx.HTTPError as exc:
            raise HTTPException(503, "Google API unavailable") from exc
    if response.status_code in {401, 403}:
        raise HTTPException(409, "Google reauthorization or additional permission is required")
    if response.status_code >= 400:
        raise HTTPException(502, "Google API request failed")
    return response


@router.get("/status")
async def google_status(
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    connection = await db.get(GoogleConnection, user["sub"])
    return {
        "connected": connection is not None,
        "email": connection.email if connection else None,
        "granted_services": granted_services(connection.scopes) if connection else [],
        "token_storage_ready": token_storage_ready(),
        "token_key_source": token_key_source(),
        "access_token_expires_at": connection.access_token_expires_at if connection else None,
    }


@router.get("/authorize")
async def authorize_google(
    services: str | None = Query(default=None),
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    selected = normalize_services(services)
    state = await create_authorization_state(db, user, selected)
    return RedirectResponse(build_authorization_url(state, selected))


@router.get("/capabilities")
async def list_capabilities(_user: dict = Depends(current_user)):
    return {"version": "1.0", "capabilities": CAPABILITIES}


def _gmail_header(message: dict, name: str) -> str:
    for item in (message.get("payload") or {}).get("headers") or []:
        if str(item.get("name", "")).lower() == name.lower():
            return str(item.get("value") or "")
    return ""


@router.get("/gmail/messages")
async def list_gmail_metadata(
    limit: int = Query(default=20, ge=1, le=50),
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    scope = SERVICE_SCOPES["gmail"][0]
    refs_response = await _request_google(
        db,
        user["sub"],
        scope,
        "GET",
        GMAIL_LIST_URL,
        params={"maxResults": limit, "q": "newer_than:30d"},
    )
    refs = refs_response.json().get("messages") or []
    messages = []
    for ref in refs[:limit]:
        message_id = str(ref.get("id") or "")
        if not message_id:
            continue
        response = await _request_google(
            db,
            user["sub"],
            scope,
            "GET",
            GMAIL_MESSAGE_URL.format(message_id=message_id),
            params=[
                ("format", "metadata"),
                ("metadataHeaders", "Subject"),
                ("metadataHeaders", "From"),
                ("metadataHeaders", "Date"),
            ],
        )
        item = response.json()
        messages.append(
            {
                "id": item.get("id"),
                "thread_id": item.get("threadId"),
                "subject": _gmail_header(item, "Subject"),
                "from": _gmail_header(item, "From"),
                "date": _gmail_header(item, "Date"),
                "internal_date": item.get("internalDate"),
                "snippet": item.get("snippet"),
            }
        )
    return {"messages": messages, "returned": len(messages)}


def _to_rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        raise HTTPException(400, "Calendar time range must include a timezone")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


@router.get("/calendar/events")
async def list_calendar_events(
    time_min: datetime,
    time_max: datetime,
    limit: int = Query(default=50, ge=1, le=250),
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    if time_max <= time_min:
        raise HTTPException(400, "time_max must be after time_min")
    response = await _request_google(
        db,
        user["sub"],
        SERVICE_SCOPES["calendar"][0],
        "GET",
        CALENDAR_EVENTS_URL,
        params={
            "timeMin": _to_rfc3339(time_min),
            "timeMax": _to_rfc3339(time_max),
            "singleEvents": "true",
            "orderBy": "startTime",
            "maxResults": limit,
        },
    )
    items = response.json().get("items") or []
    return {"events": items, "returned": len(items)}


@router.post("/calendar/events", status_code=201)
async def create_calendar_event(
    body: CalendarEventCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    payload = {
        "summary": body.summary,
        "start": {"dateTime": body.start.isoformat()},
        "end": {"dateTime": body.end.isoformat()},
    }
    if body.description:
        payload["description"] = body.description
    if body.location:
        payload["location"] = body.location
    response = await _request_google(
        db,
        user["sub"],
        SERVICE_SCOPES["calendar"][0],
        "POST",
        CALENDAR_EVENTS_URL,
        json=payload,
    )
    return response.json()


def _escape_drive_query(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


async def _ensure_drive_folder(
    db: AsyncSession,
    user_sub: str,
    name: str,
    parent_id: str | None = None,
) -> dict:
    scope = SERVICE_SCOPES["drive"][0]
    query = (
        f"name='{_escape_drive_query(name)}' and "
        "mimeType='application/vnd.google-apps.folder' and trashed=false"
    )
    if parent_id:
        query += f" and '{_escape_drive_query(parent_id)}' in parents"
    response = await _request_google(
        db,
        user_sub,
        scope,
        "GET",
        DRIVE_FILES_URL,
        params={"q": query, "spaces": "drive", "fields": "files(id,name)"},
    )
    files = response.json().get("files") or []
    if files:
        return files[0]
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]
    response = await _request_google(
        db,
        user_sub,
        scope,
        "POST",
        DRIVE_FILES_URL,
        params={"fields": "id,name"},
        json=metadata,
    )
    return response.json()


@router.post("/drive/bridge", status_code=201)
async def ensure_drive_bridge(
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    root = await _ensure_drive_folder(db, user["sub"], "life_assistant")
    bridge = await _ensure_drive_folder(db, user["sub"], "ChatGPT_Bridge", root.get("id"))
    return {
        "root": {"id": root.get("id"), "name": root.get("name")},
        "bridge": {"id": bridge.get("id"), "name": bridge.get("name")},
    }
