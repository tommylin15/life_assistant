"""Manual-only Gmail action radar; never schedules or fetches entire mailboxes."""
import re
from datetime import datetime, timezone
from urllib.parse import quote
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user
from app.api.google_integrations import (
    GMAIL_LIST_URL, GMAIL_MESSAGE_URL, _gmail_header, _request_google,
)
from app.db.session import get_db
from app.models.gmail_radar import GmailRadarItem, GmailRadarScanState
from app.models.google_integration import GoogleConnection
from app.services.google_oauth import SERVICE_SCOPES

router = APIRouter(prefix="/integrations/google/gmail/radar", tags=["gmail-radar"])

# Precision-first rules: an ambiguous promotion must not become a pending item.
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("billing", ("繳費期限", "繳費通知", "繳款通知", "繳款截止", "付款期限", "付款提醒",
                 "帳單到期", "payment due", "bill due", "statement due")),
    ("pickup", ("取貨通知", "取貨期限", "包裹已到", "貨到門市", "package ready", "ready for pickup")),
    ("booking", ("訂房確認", "訂位確認", "預約確認", "預約成功", "booking confirmation",
                 "reservation confirmed", "appointment confirmed")),
    ("travel", ("航班異動", "航班取消", "機票訂位", "航班確認", "flight canceled",
                "flight cancelled", "flight change")),
    ("deadline", ("報名截止", "補件通知", "請於期限內", "申請期限", "registration deadline",
                  "action required", "response required")),
)
_PROMOTION = re.compile(r"(?i)(unsubscribe|取消訂閱|特賣|限時優惠|促銷|折扣碼|廣告 EDM)")


def classify_message(subject: str, snippet: str) -> str | None:
    """Only surface explicit, actionable intent, not every incoming email."""
    title = " ".join(subject.lower().split())
    preview = " ".join(snippet.lower().split())[:500]
    if not title:
        return None
    for category, phrases in _RULES:
        if any(phrase.lower() in title for phrase in phrases):
            return category
    if _PROMOTION.search(title):
        return None
    # Snippets are weaker evidence; require a precise actionable phrase.
    for category, phrases in _RULES:
        if any(phrase.lower() in preview for phrase in phrases[:3]):
            return category
    return None


def gmail_urls(thread_id: str, email: str) -> dict[str, str]:
    # The #all/<thread> Gmail route works on some web clients. It is not a
    # guaranteed API-to-web mapping; always provide a safe mailbox fallback.
    authuser = quote(email, safe="")
    return {
        "gmail_url": f"https://mail.google.com/mail/?authuser={authuser}#all/{quote(thread_id, safe='')}",
        "gmail_fallback_url": f"https://mail.google.com/mail/?authuser={authuser}#all",
    }


def _serialize_item(item: GmailRadarItem, email: str) -> dict:
    return {
        "id": item.id, "category": item.category, "title": item.title,
        "summary": item.summary, "sender": item.sender, "status": item.status,
        "received_at": item.received_at, "created_at": item.created_at,
        **gmail_urls(item.gmail_thread_id, email),
    }


def _serialize_state(state: GmailRadarScanState | None) -> dict:
    if state is None:
        return {"status": "never_scanned", "checked": 0, "added": 0,
                "skipped": 0, "failed": 0, "last_started_at": None,
                "last_finished_at": None}
    return {
        "status": state.status,
        "checked": state.checked, "added": state.added,
        "skipped": state.skipped, "failed": state.failed,
        "last_started_at": state.last_started_at,
        "last_finished_at": state.last_finished_at,
    }


@router.get("/items")
async def get_radar_items(
    status: Literal["pending", "completed", "ignored", "all"] = "pending",
    limit: int = Query(default=50, ge=1, le=100),
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(GmailRadarItem).where(GmailRadarItem.user_sub == user["sub"])
    if status != "all":
        stmt = stmt.where(GmailRadarItem.status == status)
    stmt = stmt.order_by(GmailRadarItem.created_at.desc()).limit(limit)
    items = (await db.execute(stmt)).scalars().all()
    connection = await db.get(GoogleConnection, user["sub"])
    email = connection.email if connection else str(user.get("email") or "")
    return {"items": [_serialize_item(item, email) for item in items], "returned": len(items)}


@router.get("/status")
async def get_radar_status(
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    state = await db.get(GmailRadarScanState, user["sub"])
    connection = await db.get(GoogleConnection, user["sub"])
    authorized = bool(connection and SERVICE_SCOPES["gmail"][0] in set(connection.scopes.split()))
    return {"gmail_authorized": authorized, **_serialize_state(state)}


class RadarItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["pending", "completed", "ignored"]


@router.patch("/items/{item_id}")
async def update_radar_item(
    item_id: str,
    body: RadarItemUpdate,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    item = await db.scalar(select(GmailRadarItem).where(
        GmailRadarItem.id == item_id, GmailRadarItem.user_sub == user["sub"],
    ))
    if item is None:
        raise HTTPException(404, "Gmail radar item not found")
    item.status = body.status
    await db.commit()
    connection = await db.get(GoogleConnection, user["sub"])
    email = connection.email if connection else str(user.get("email") or "")
    return {"item": _serialize_item(item, email)}


@router.post("/quick-scan")
async def manual_quick_scan(
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Bounded synchronous manual scan; no cron, job, background task or AI body upload."""
    sub = user["sub"]
    # xact advisory lock also serializes two web sessions of the same user.
    # Neither the API nor its body accepts a target account.
    locked = (await db.execute(
        text("SELECT pg_try_advisory_xact_lock(5623, hashtext(:sub))"),
        {"sub": sub},
    )).scalar_one()
    if not locked:
        raise HTTPException(409, "This account already has a Gmail scan in progress")

    connection = await db.get(GoogleConnection, sub)
    if connection is None or SERVICE_SCOPES["gmail"][0] not in set(connection.scopes.split()):
        raise HTTPException(409, "Please authorize Gmail in Google service connections")

    now = datetime.now(timezone.utc)
    checked, added, skipped, failed = 0, 0, 0, 0
    scope = SERVICE_SCOPES["gmail"][0]
    response = await _request_google(
        db, sub, scope, "GET", GMAIL_LIST_URL,
        params={"q": "newer_than:7d -in:spam -in:trash", "maxResults": 20},
        preserve_transaction=True,
    )
    ids = [str(item["id"]) for item in response.json().get("messages", [])
           if isinstance(item, dict) and item.get("id")][:20]

    for message_id in ids:
        checked += 1
        existing = await db.scalar(select(GmailRadarItem.id).where(
            GmailRadarItem.user_sub == sub,
            GmailRadarItem.gmail_message_id == message_id,
        ))
        if existing:
            skipped += 1
            continue
        try:
            response = await _request_google(
                db, sub, scope, "GET",
                GMAIL_MESSAGE_URL.format(message_id=quote(message_id, safe="")),
                params=[("format", "metadata"),
                        ("metadataHeaders", "Subject"),
                        ("metadataHeaders", "From"),
                        ("metadataHeaders", "Date")],
                preserve_transaction=True,
            )
            raw = response.json()
            subject = _gmail_header(raw, "Subject").strip()[:500]
            snippet = str(raw.get("snippet") or "").strip()[:500]
            category = classify_message(subject, snippet)
            if not category:
                skipped += 1
                continue
            stamp = raw.get("internalDate")
            received_at = None
            if stamp is not None:
                try:
                    received_at = datetime.fromtimestamp(int(stamp) / 1000, tz=timezone.utc)
                except (ValueError, TypeError, OverflowError):
                    pass
            item = GmailRadarItem(
                user_sub=sub, gmail_message_id=message_id,
                gmail_thread_id=str(raw.get("threadId") or message_id),
                category=category, title=subject or "Gmail 待確認事項",
                summary=snippet[:320], sender=_gmail_header(raw, "From")[:320],
                status="pending", received_at=received_at,
            )
            db.add(item)
            added += 1
        except HTTPException as exc:
            if exc.status_code in (401, 403, 409):
                raise
            failed += 1
        except (ValueError, TypeError, KeyError):
            failed += 1

    state = await db.get(GmailRadarScanState, sub)
    if state is None:
        state = GmailRadarScanState(user_sub=sub, status="succeeded")
        db.add(state)
    state.status = "partial" if failed else "succeeded"
    state.last_started_at = now
    state.last_finished_at = datetime.now(timezone.utc)
    state.checked = checked
    state.added = added
    state.skipped = skipped
    state.failed = failed
    await db.commit()
    return {"source": "rules", "scan_window_days": 7, "limit": 20,
            **_serialize_state(state)}
