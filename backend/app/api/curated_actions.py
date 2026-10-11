"""Explicit account-owned actions. Shared imports never create personal entries."""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, Query
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.api.ui_policies import _audit
from app.api.google_integrations import _request_google, CALENDAR_EVENTS_URL, SERVICE_SCOPES
from app.db.session import get_db
from app.models.curated import CuratedActivity
from app.models.curated_actions import CuratedPersonalAction
from app.models.task import Task
from app.api.curated import normalize_url

router = APIRouter(prefix="/free-events/curated", tags=["curated-personal-actions"])
KINDS = Literal["save", "follow", "task", "calendar_info", "calendar_registration", "calendar_confirmed", "reminder"]


async def activity_access(user: dict = Depends(current_user), db: AsyncSession = Depends(get_db)):
    from app.api.ui_policies import effective_features
    features = await effective_features(db, user)
    if not any(f["available"] for f in features if f["key"] in ("events", "opportunities", "explore")):
        raise HTTPException(403, "Activity features unavailable")
    return user


class ActionWrite(BaseModel):
    model_config = ConfigDict(extra="forbid")
    active: bool
    start: datetime | None = None
    end: datetime | None = None
    phase: Literal["open", "deadline"] = "open"
    lead_minutes: int = Field(60, ge=0, le=10080)
    tracking_status: Literal["interested", "waiting", "submitted", "confirmed", "waitlisted", "failed", "cancelled"] = "interested"
    task_due_choice: Literal["none", "open", "deadline", "custom"] = "none"
    task_due_at: datetime | None = None
    task_title: str | None = Field(default=None, max_length=400)
    @model_validator(mode="after")
    def times(self):
        if (self.start is None) != (self.end is None):
            raise ValueError("start_end_pair_required")
        if self.start and (self.start.utcoffset() is None or self.end.utcoffset() is None or self.end <= self.start):
            raise ValueError("invalid_confirmed_times")
        if self.task_due_at is not None and self.task_due_at.utcoffset() is None:
            raise ValueError("Task due date must include timezone")
        if self.task_due_choice == "custom" and self.task_due_at is None:
            raise ValueError("Custom task date is missing")
        return self


def _item_url(item) -> str:
    details = item.handoff_details or {}
    preferred = details.get("registration_url") or details.get("official_url")
    if isinstance(preferred, str):
        try:
            return normalize_url(preferred)
        except ValueError:
            pass
    return normalize_url(item.original_url)


def _task_due(item, body):
    details = item.handoff_details or {}
    if body.task_due_choice == "none":
        return None
    if body.task_due_choice == "custom":
        return body.task_due_at
    if body.task_due_choice == "deadline":
        raw = details.get("registration_deadline_at_tpe")
        if item.registration_deadline is not None:
            return item.registration_deadline
    else:
        raw = details.get("registration_open_at_tpe")
    if not isinstance(raw, str) or "T" not in raw:
        raise HTTPException(422, "Selected registration time is not available")
    try:
        parsed = datetime.fromisoformat(raw)
        if parsed.utcoffset() is None:
            raise ValueError("tz")
        return parsed
    except ValueError as exc:
        raise HTTPException(422, "Selected registration time is unverified") from exc


def calendar_payload(item, kind, body):
    details = item.handoff_details or {}
    prefix = {"calendar_info": "活動日期參考", "calendar_registration": "報名時間提醒",
              "calendar_confirmed": "確定參與", "reminder": "報名預警"}[kind]
    payload = {"summary": f"{prefix}：{item.title}",
               "description": f"活動網址：{_item_url(item)}", 
               "location": details.get("venue") or None,
               "transparency": "opaque" if kind == "calendar_confirmed" else "transparent",
               "reminders": {"useDefault": False, "overrides": []}}
    if kind == "calendar_info":
        if not item.starts_on:
            raise HTTPException(422, "Activity date is unknown")
        payload.update(start={"date": item.starts_on.isoformat()},
                       end={"date": ((item.ends_on or item.starts_on) + timedelta(days=1)).isoformat()})
    elif kind == "calendar_confirmed":
        if not body.start:
            raise HTTPException(422, "Select actual participation times")
        payload.update(start={"dateTime": body.start.isoformat()}, end={"dateTime": body.end.isoformat()})
    else:
        raw = details.get("registration_open_at_tpe" if body.phase == "open" else "registration_deadline_at_tpe")
        if not raw or "T" not in raw:
            raise HTTPException(422, "Verified registration time is unknown")
        moment = datetime.fromisoformat(raw)
        if moment <= datetime.now(timezone.utc):
            raise HTTPException(422, "Registration time has passed")
        if kind == "reminder" and moment - timedelta(minutes=body.lead_minutes) <= datetime.now(timezone.utc):
            raise HTTPException(422, "Advance reminder time has passed")
        payload.update(start={"dateTime": moment.isoformat()}, end={"dateTime": (moment + timedelta(minutes=15)).isoformat()})
        if kind == "reminder":
            payload["reminders"]["overrides"] = [{"method": "popup", "minutes": body.lead_minutes}]
    return payload


@router.get("/actions")
async def my_actions(response: Response, user: dict = Depends(activity_access), db: AsyncSession = Depends(get_db),
                     activity_ids: str | None = Query(None, max_length=6500)):
    statement = select(CuratedPersonalAction).where(CuratedPersonalAction.user_sub == user["sub"])
    if isinstance(activity_ids, str) and activity_ids:
        ids = activity_ids.split(",")
        if len(ids) > 100 or any(len(i) != 64 or not all(c in "0123456789abcdef" for c in i) for i in ids):
            raise HTTPException(422, "Invalid activity id list")
        statement = statement.where(CuratedPersonalAction.activity_id.in_(ids))
    else:
        # Compatibility callers are bounded; V3 passes explicit page IDs.
        statement = statement.order_by(CuratedPersonalAction.updated_at.desc()).limit(1000)
    rows = (await db.execute(statement)).scalars().all()
    response.headers["Cache-Control"] = "no-store"
    return {"items": [{"activity_id": r.activity_id, "kind": r.kind, "active": r.active,
                       "entity_id": r.entity_id, "payload": r.payload} for r in rows]}


@router.put("/{activity_id}/actions/{kind}")
async def set_action(activity_id: str, kind: KINDS, body: ActionWrite,
                     user: dict = Depends(activity_access), db: AsyncSession = Depends(get_db)):
    item = await db.get(CuratedActivity, activity_id)
    if item is None:
        raise HTTPException(404, "Activity not found")
    lock = int.from_bytes(hashlib.sha256(f"curated-actions:{user['sub']}".encode()).digest()[:8], "big", signed=True)
    await db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock})
    if kind == "save":
        # A single bookmark belongs to a parent event. Preserve old child saves
        # and collapse them when the user next toggles that parent.
        group = item.parent_event_key or item.handoff_event_key
        if group:
            siblings = (await db.execute(select(CuratedActivity).where(
                (CuratedActivity.parent_event_key == group) |
                (CuratedActivity.handoff_event_key == group)
            ))).scalars().all()
            parent = next((r for r in siblings
                if (r.handoff_details or {}).get("record_type") == "main"), None)
            item = parent or min(siblings, key=lambda r: r.identity_key, default=item)
            # Stable synthetic ID is independent of canonical URL and changing
            # child identities. Prefix distinguishes it from 64-hex URL keys.
            group_identity = "handoff:" + group
            activity_id = "g:" + hashlib.sha256(group_identity.encode()).hexdigest()[:62]
            old_saves = (await db.execute(select(CuratedPersonalAction).where(
                CuratedPersonalAction.user_sub == user["sub"],
                CuratedPersonalAction.kind == "save",
                CuratedPersonalAction.activity_id.in_([r.identity_key for r in siblings])
            ))).scalars().all()
            for old in old_saves:
                old.active = False
        else:
            group_identity = None
    key = (user["sub"], activity_id, kind)
    record = await db.get(CuratedPersonalAction, key)
    payload = body.model_dump(mode="json")
    if kind == "save" and group_identity:
        # Postgres lookup follows parent_group even when its URL/identity changes.
        payload["parent_group"] = group_identity
    if not body.active and record and record.payload.get("calendar_group"):
        payload["calendar_group"] = record.payload["calendar_group"]
    same_payload = record is not None and all(record.payload.get(k) == v for k, v in payload.items())
    if record and record.active == body.active and kind != "save" and not (kind == "follow" and body.active and not same_payload):
        if body.active and not same_payload:
            raise HTTPException(409, "Cancel the previous action before choosing new times")
        return {"active": record.active, "entity_id": record.entity_id, "unchanged": True}
    if record is None:
        record = CuratedPersonalAction(user_sub=user["sub"], activity_id=activity_id, kind=kind, active=False, payload={})
        db.add(record)
    if kind == "task":
        if body.active:
            # No deadline is silently invented; user explicitly confirms the choice.
            title = (body.task_title or f"處理活動：{item.title}").strip()
            if not title:
                raise HTTPException(422, "Task title is required")
            url = _item_url(item)
            note = f"活動網址：{url}"
            task = Task(id=str(uuid.uuid4()), user_sub=user["sub"], title=title,
                        note=note, source_type="curated", source_ref=item.identity_key,
                        due_at=_task_due(item, body))
            db.add(task)
            record.entity_id = task.id
            payload["generated_title"] = title
            payload["generated_note"] = note
        elif record.entity_id:
            task = await db.get(Task, record.entity_id)
            if task and task.user_sub == user["sub"]:
                # Do not overwrite/delete a personally edited Task.
                prior = record.payload or {}
                if (prior.get("generated_title") == task.title and
                    prior.get("generated_note") == task.note):
                    task.status = "cancelled"
    elif kind.startswith("calendar_") or kind == "reminder":
        if body.active:
            event_payload = calendar_payload(item, kind, body)
            # Group same-parent, same-phase notifications without combining
            # distinct offers in the activity database.
            group = item.parent_event_key or item.handoff_event_key or activity_id
            # The event links to the exact selected child/offer, never an
            # ambiguous list of unrelated sibling registration URLs.
            time_key = event_payload["start"]
            namespace = "handoff" if item.handoff_event_key else "legacy"
            calendar_group = hashlib.sha256(f"{user['sub']}:{namespace}:{group}:{kind}:{body.phase}:{time_key}:{body.lead_minutes}".encode()).hexdigest()
            group_query = select(CuratedPersonalAction).where(CuratedPersonalAction.user_sub == user["sub"],
                CuratedPersonalAction.payload["calendar_group"].as_string() == calendar_group)
            # Every reactivation gets a new lifecycle ID. Retries after a DB
            # failure reuse that ID; siblings reuse the active parent's event.
            members = (await db.execute(group_query)).scalars().all()
            active_member = next((r for r in members if r.active), None)
            latest = max((r.updated_at for r in members if r.updated_at), default=None)
            generation = latest.isoformat() if latest else "initial"
            event_id = active_member.entity_id if active_member else hashlib.sha256(f"{calendar_group}:{generation}".encode()).hexdigest()
            payload["calendar_group"] = calendar_group
            url = CALENDAR_EVENTS_URL + "/" + event_id
            existing = await _request_google(db, user["sub"], SERVICE_SCOPES["calendar"][0], "GET", url, preserve_transaction=True, allowed_status=(404, 410))
            if existing.status_code in (404, 410):
                created = await _request_google(db, user["sub"], SERVICE_SCOPES["calendar"][0], "POST", CALENDAR_EVENTS_URL, preserve_transaction=True,
                    json={**event_payload, "id": event_id}, allowed_status=(409,))
                if created.status_code == 409:
                    await _request_google(db, user["sub"], SERVICE_SCOPES["calendar"][0], "GET", url, preserve_transaction=True)
            record.entity_id = event_id
        elif record.entity_id:
            other = await db.scalar(select(CuratedPersonalAction).where(
                CuratedPersonalAction.user_sub == user["sub"], CuratedPersonalAction.entity_id == record.entity_id,
                CuratedPersonalAction.active.is_(True), CuratedPersonalAction.activity_id != activity_id))
            if other is None:
                await _request_google(db, user["sub"], SERVICE_SCOPES["calendar"][0], "DELETE",
                    CALENDAR_EVENTS_URL + "/" + record.entity_id, preserve_transaction=True, allowed_status=(404, 410))
    record.active = body.active
    record.payload = payload
    record.updated_at = datetime.now(timezone.utc)
    _audit(db, user["sub"], "curated.personal_action", f"kind={kind} active={body.active}")
    await db.commit()
    return {"active": record.active, "entity_id": record.entity_id, "unchanged": False}
