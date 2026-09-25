import uuid
from datetime import datetime, timezone
from urllib.parse import quote

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.google_integration import GoogleConnection
from app.models.task import Task, TaskPriority
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
        "required_scopes": [SERVICE_SCOPES["gmail"][0]],
        "risk": "read",
        "confirmation": "none",
    },
    {
        "name": "gmail.to_task",
        "version": "1.0",
        "service": "gmail",
        "required_scope": SERVICE_SCOPES["gmail"][0],
        "required_scopes": [SERVICE_SCOPES["gmail"][0]],
        "risk": "write_internal",
        "confirmation": "explicit_user_or_policy",
    },
    {
        "name": "gmail.to_calendar",
        "version": "1.0",
        "service": "gmail+calendar",
        "required_scope": SERVICE_SCOPES["gmail"][0],
        "required_scopes": [
            SERVICE_SCOPES["gmail"][0],
            SERVICE_SCOPES["calendar"][0],
        ],
        "risk": "write_external",
        "confirmation": "explicit_user_or_policy",
    },
    {
        "name": "calendar.list",
        "version": "1.0",
        "service": "calendar",
        "required_scope": SERVICE_SCOPES["calendar"][0],
        "required_scopes": [SERVICE_SCOPES["calendar"][0]],
        "risk": "read",
        "confirmation": "none",
    },
    {
        "name": "calendar.create",
        "version": "1.0",
        "service": "calendar",
        "required_scope": SERVICE_SCOPES["calendar"][0],
        "required_scopes": [SERVICE_SCOPES["calendar"][0]],
        "risk": "write_external",
        "confirmation": "explicit_user_or_policy",
    },
    {
        "name": "calendar.update",
        "version": "1.0",
        "service": "calendar",
        "required_scope": SERVICE_SCOPES["calendar"][0],
        "required_scopes": [SERVICE_SCOPES["calendar"][0]],
        "risk": "write_external",
        "confirmation": "explicit_user_or_policy",
    },
    {
        "name": "calendar.delete",
        "version": "1.0",
        "service": "calendar",
        "required_scope": SERVICE_SCOPES["calendar"][0],
        "required_scopes": [SERVICE_SCOPES["calendar"][0]],
        "risk": "destructive_external",
        "confirmation": "explicit_user",
    },
    {
        "name": "drive.bridge.ensure",
        "version": "1.0",
        "service": "drive",
        "required_scope": SERVICE_SCOPES["drive"][0],
        "required_scopes": [SERVICE_SCOPES["drive"][0]],
        "risk": "write_limited",
        "confirmation": "explicit_user_or_policy",
    },
]

GMAIL_LIST_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
GMAIL_MESSAGE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/{message_id}"
CALENDAR_EVENTS_URL = "https://www.googleapis.com/calendar/v3/calendars/primary/events"
CALENDAR_EVENT_URL = (
    "https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}"
)
DRIVE_FILES_URL = "https://www.googleapis.com/drive/v3/files"


def _validate_calendar_times(start: datetime, end: datetime) -> None:
    if start.tzinfo is None or end.tzinfo is None:
        raise ValueError("Calendar event times must include a timezone")
    if end <= start:
        raise ValueError("Calendar event end must be after start")


class CalendarEventCreate(BaseModel):
    summary: str = Field(min_length=1, max_length=500)
    start: datetime
    end: datetime
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_times(self):
        _validate_calendar_times(self.start, self.end)
        return self


class CalendarEventUpdate(BaseModel):
    summary: str | None = Field(default=None, min_length=1, max_length=500)
    start: datetime | None = None
    end: datetime | None = None
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_update(self):
        fields = self.model_fields_set
        if not fields:
            raise ValueError("At least one Calendar event field must be provided")
        if "summary" in fields and self.summary is None:
            raise ValueError("Calendar event summary cannot be null")
        has_start = "start" in fields
        has_end = "end" in fields
        if has_start != has_end:
            raise ValueError("Calendar event start and end must be updated together")
        if has_start:
            if self.start is None or self.end is None:
                raise ValueError("Calendar event start and end cannot be null")
            _validate_calendar_times(self.start, self.end)
        return self


class GmailToTaskCreate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=500)
    note: str | None = Field(default=None, max_length=5000)
    priority: TaskPriority = TaskPriority.normal
    due_at: datetime | None = None
    reminder_at: datetime | None = None


class GmailToCalendarCreate(BaseModel):
    start: datetime
    end: datetime
    summary: str | None = Field(default=None, min_length=1, max_length=500)
    description: str | None = Field(default=None, max_length=5000)
    location: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_times(self):
        _validate_calendar_times(self.start, self.end)
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
        raise HTTPException(
            409, "Google reauthorization or additional permission is required"
        )
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
        "access_token_expires_at": (
            connection.access_token_expires_at if connection else None
        ),
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


async def _get_gmail_metadata(
    db: AsyncSession,
    user_sub: str,
    message_id: str,
) -> dict:
    response = await _request_google(
        db,
        user_sub,
        SERVICE_SCOPES["gmail"][0],
        "GET",
        GMAIL_MESSAGE_URL.format(message_id=quote(message_id, safe="")),
        params=[
            ("format", "metadata"),
            ("metadataHeaders", "Subject"),
            ("metadataHeaders", "From"),
            ("metadataHeaders", "Date"),
        ],
    )
    item = response.json()
    return {
        "id": item.get("id"),
        "thread_id": item.get("threadId"),
        "subject": _gmail_header(item, "Subject"),
        "from": _gmail_header(item, "From"),
        "date": _gmail_header(item, "Date"),
        "internal_date": item.get("internalDate"),
        "snippet": item.get("snippet"),
    }


def _gmail_source_note(message: dict) -> str:
    lines = ["Source: Gmail"]
    for label, key in (
        ("Message ID", "id"),
        ("Thread ID", "thread_id"),
        ("From", "from"),
        ("Date", "date"),
    ):
        value = str(message.get(key) or "").strip()
        if value:
            lines.append(f"{label}: {value}")
    snippet = str(message.get("snippet") or "").strip()
    if snippet:
        lines.extend(["", snippet])
    return "\n".join(lines)


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
        messages.append(await _get_gmail_metadata(db, user["sub"], message_id))
    return {"messages": messages, "returned": len(messages)}


@router.post("/gmail/messages/{message_id}/task", status_code=201)
async def gmail_message_to_task(
    message_id: str,
    body: GmailToTaskCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    message = await _get_gmail_metadata(db, user["sub"], message_id)
    source_note = _gmail_source_note(message)
    note = source_note if not body.note else f"{body.note}\n\n{source_note}"
    title = (body.title or str(message.get("subject") or "").strip() or "Gmail message")[
        :500
    ]
    task = Task(
        id=str(uuid.uuid4()),
        title=title,
        note=note,
        priority=body.priority,
        due_at=body.due_at,
        reminder_at=body.reminder_at,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return {
        "task": {
            "id": task.id,
            "title": task.title,
            "note": task.note,
            "status": task.status,
            "priority": task.priority,
            "due_at": task.due_at,
            "reminder_at": task.reminder_at,
            "project_id": task.project_id,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
        },
        "source": {
            "gmail_message_id": message.get("id"),
            "thread_id": message.get("thread_id"),
        },
    }


def _to_rfc3339(value: datetime) -> str:
    if value.tzinfo is None:
        raise HTTPException(400, "Calendar time range must include a timezone")
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _calendar_create_payload(
    summary: str,
    start: datetime,
    end: datetime,
    description: str | None,
    location: str | None,
) -> dict:
    payload = {
        "summary": summary,
        "start": {"dateTime": start.isoformat()},
        "end": {"dateTime": end.isoformat()},
    }
    if description is not None:
        payload["description"] = description
    if location is not None:
        payload["location"] = location
    return payload


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
    response = await _request_google(
        db,
        user["sub"],
        SERVICE_SCOPES["calendar"][0],
        "POST",
        CALENDAR_EVENTS_URL,
        json=_calendar_create_payload(
            body.summary,
            body.start,
            body.end,
            body.description,
            body.location,
        ),
    )
    return response.json()


@router.patch("/calendar/events/{event_id}")
async def update_calendar_event(
    event_id: str,
    body: CalendarEventUpdate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    fields = body.model_fields_set
    payload: dict = {}
    if "summary" in fields:
        payload["summary"] = body.summary
    if "description" in fields:
        payload["description"] = body.description
    if "location" in fields:
        payload["location"] = body.location
    if "start" in fields:
        payload["start"] = {"dateTime": body.start.isoformat()}
        payload["end"] = {"dateTime": body.end.isoformat()}

    response = await _request_google(
        db,
        user["sub"],
        SERVICE_SCOPES["calendar"][0],
        "PATCH",
        CALENDAR_EVENT_URL.format(event_id=quote(event_id, safe="")),
        json=payload,
    )
    return response.json()


@router.delete("/calendar/events/{event_id}", status_code=204)
async def delete_calendar_event(
    event_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    await _request_google(
        db,
        user["sub"],
        SERVICE_SCOPES["calendar"][0],
        "DELETE",
        CALENDAR_EVENT_URL.format(event_id=quote(event_id, safe="")),
    )
    return Response(status_code=204)


@router.post("/gmail/messages/{message_id}/calendar", status_code=201)
async def gmail_message_to_calendar(
    message_id: str,
    body: GmailToCalendarCreate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    message = await _get_gmail_metadata(db, user["sub"], message_id)
    source_note = _gmail_source_note(message)
    description = (
        source_note if not body.description else f"{body.description}\n\n{source_note}"
    )
    summary = (
        body.summary or str(message.get("subject") or "").strip() or "Gmail message"
    )[:500]

    response = await _request_google(
        db,
        user["sub"],
        SERVICE_SCOPES["calendar"][0],
        "POST",
        CALENDAR_EVENTS_URL,
        json=_calendar_create_payload(
            summary,
            body.start,
            body.end,
            description,
            body.location,
        ),
    )
    event = response.json()
    return {
        "event": event,
        "source": {
            "gmail_message_id": message.get("id"),
            "thread_id": message.get("thread_id"),
        },
    }


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
    bridge = await _ensure_drive_folder(
        db, user["sub"], "ChatGPT_Bridge", root.get("id")
    )
    return {
        "root": {"id": root.get("id"), "name": root.get("name")},
        "bridge": {"id": bridge.get("id"), "name": bridge.get("name")},
    }
