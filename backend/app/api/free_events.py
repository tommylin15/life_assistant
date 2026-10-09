"""Authenticated, read-only verified free-event catalog and owner-only aggregates."""
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.db.session import get_db
from app.models.free_event_discovery_schemas import FreeEventDiscoveryOut
from app.services.free_events_discovery import list_verified_public_events
from scripts.read_free_events_status import readback as read_free_events_status

router = APIRouter(prefix="/free-events", tags=["free-events"])


@router.get("", response_model=FreeEventDiscoveryOut)
async def list_free_events(
    response: Response,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=5000),
    _user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    events = await list_verified_public_events(
        db, limit=limit, offset=offset, now=now,
    )
    response.headers["Cache-Control"] = "no-store"
    return FreeEventDiscoveryOut(
        items=events, returned=len(events), last_updated_at=now,
    )


@router.get("/status")
async def free_events_owner_status(
    response: Response,
    user: dict = Depends(current_user),
):
    """Aggregate-only owner readback; no Cloud Logging reader or DB writes.

    Deny when the production owner allowlist is missing; no unguarded admin
    endpoint, even for otherwise valid Google sessions.
    """
    approved = os.environ.get("ALLOWED_GOOGLE_EMAIL", "").strip().lower()
    actual = str(user.get("email", "")).strip().lower()
    if not approved or actual != approved:
        raise HTTPException(status_code=403, detail="Owner access required")
    result = await read_free_events_status()
    response.headers["Cache-Control"] = "no-store"
    return result
