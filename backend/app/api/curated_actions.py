"""Explicit account-owned actions. Shared imports never create personal entries."""
import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response
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
    @model_validator(mode="after")
    def times(self):
        if (self.start is None) != (self.end is None):
            raise ValueError("start_end_pair_required")
        if self.start and (self.start.utcoffset() is None or self.end.utcoffset() is None or self.end <= self.start):
            raise ValueError("invalid_confirmed_times")
        return self


def calendar_payload(item, kind, body):
    details = item.handoff_details or {}
    prefix = {"calendar_info": "活動日期參考", "calendar_registration": "報名時間提醒",
              "calendar_confirmed": "確定參與", "reminder": "報名預警"}[kind]
    payload = {"summary": f"{prefix}：{item.title}", "description": item.original_url,
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
async def my_actions(response: Response, user: dict = Depends(activity_access), db: AsyncSession = Depends(get_db)):
    # shortcut: return at most 1000 actions per account; paginate before offering larger personal libraries.
    rows = (await db.execute(select(CuratedPersonalAction).where(CuratedPersonalAction.user_sub == user["sub"]).limit(1000))).scalars().all()
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
    key = (user["sub"], activity_id, kind)
    record = await db.get(CuratedPersonalAction, key)
    payload = body.model_dump(mode="json")
    if not body.active and record and record.payload.get("calendar_group"):
        payload["calendar_group"] = record.payload["calendar_group"]
    same_payload = record is not None and all(record.payload.get(k) == v for k, v in payload.items())
    if record and record.active == body.active and not (kind == "follow" and body.active and not same_payload):
        if body.active and not same_payload:
            raise HTTPException(409, "Cancel the previous action before choosing new times")
        return {"active": record.active, "entity_id": record.entity_id, "unchanged": True}
    if record is None:
        record = CuratedPersonalAction(user_sub=user["sub"], activity_id=activity_id, kind=kind, active=False, payload={})
        db.add(record)
    if kind == "task":
        if body.active:
            # A stable action row + transaction lock prevents retry duplicates.
            task = Task(id=str(uuid.uuid4()), user_sub=user["sub"], title=f"處理活動：{item.title}",
                        note=item.original_url, source_type="curated", source_ref=item.identity_key,
                        due_at=item.registration_deadline)
            db.add(task)
            record.entity_id = task.id
        elif record.entity_id:
            task = await db.get(Task, record.entity_id)
            if task and task.user_sub == user["sub"]:
                # Keep a user-edited personal copy; explicit cancel only cancels
                # the original generated task rather than deleting user data.
                task.status = "cancelled"
    elif kind.startswith("calendar_") or kind == "reminder":
        if body.active:
            event_payload = calendar_payload(item, kind, body)
            # Group same-parent, same-phase notifications without combining
            # distinct offers in the activity database.
            group = item.parent_event_key or item.handoff_event_key or activity_id
            if item.handoff_event_key:
                siblings = (await db.execute(select(CuratedActivity).where(
                    (CuratedActivity.handoff_event_key == group) | (CuratedActivity.parent_event_key == group)
                ))).scalars().all()
                links = {item.original_url}
                for sibling in siblings:
                    links.add(sibling.original_url)
                    if (sibling.handoff_details or {}).get("registration_url"):
                        links.add(sibling.handoff_details["registration_url"])
                event_payload["description"] = "\n".join(sorted(links))
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
