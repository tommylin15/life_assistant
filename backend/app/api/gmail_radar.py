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
from app.models.gmail_radar import GmailRadarItem, GmailRadarScanState, GmailRadarSeen
from app.models.execution_log import ExecutionLog
from app.models.google_integration import GoogleConnection
from app.services.google_oauth import SERVICE_SCOPES

router = APIRouter(prefix="/integrations/google/gmail/radar", tags=["gmail-radar"])

QUICK_LIMIT = 20
BACKFILL_BATCH = 40
THREE_DAY_PAGE_SIZE = 500
THREE_DAY_MAX_PAGES = 4
THREE_DAY_QUERY = "newer_than:3d -in:spam -in:trash"
QUICK_QUERY = "newer_than:7d -in:spam -in:trash"


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


_TARGET_ROUTES = {
    "task": "/tasks",
    "note": "/more/notes",
    "shopping": "/more/shopping",
    "calendar": "/calendar",
}


def _target_route(target: str | None) -> str | None:
    return _TARGET_ROUTES.get(target)


def _handoff_action_id(item_id: str) -> str:
    # Stable ID: repeat presses never create a second Life entity.
    return "gmailradar-" + item_id.replace("-", "")


def _serialize_item(item: GmailRadarItem, email: str) -> dict:
    return {
        "id": item.id, "category": item.category, "title": item.title,
        "summary": item.summary, "sender": item.sender, "status": item.status,
        "received_at": item.received_at, "created_at": item.created_at,
        "linked_target": item.linked_target,
        "linked_entity_id": item.linked_entity_id,
        "linked_route": _target_route(item.linked_target) if item.linked_entity_id else None,
        **gmail_urls(item.gmail_thread_id, email),
    }


def _serialize_state(state: GmailRadarScanState | None) -> dict:
    if state is None:
        return {"status": "never_scanned", "checked": 0, "added": 0,
                "skipped": 0, "failed": 0, "last_started_at": None,
                "last_finished_at": None, "scan_kind": None,
                "three_day_count": None, "three_day_remaining": None,
                "three_day_complete": False}
    return {
        "status": state.status,
        "checked": state.checked, "added": state.added,
        "skipped": state.skipped, "failed": state.failed,
        "last_started_at": state.last_started_at,
        "last_finished_at": state.last_finished_at,
        "scan_kind": state.scan_kind,
        "three_day_count": state.three_day_count,
        "three_day_remaining": state.three_day_remaining,
        "three_day_complete": state.three_day_complete,
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


@router.get("/items/{item_id}/handoff")
async def get_item_for_life_inbox(
    item_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Only owner-scoped source metadata; no Gmail body or token exposed."""
    item = await db.scalar(select(GmailRadarItem).where(
        GmailRadarItem.id == item_id, GmailRadarItem.user_sub == user["sub"],
    ))
    if item is None:
        raise HTTPException(404, "Gmail radar item not found")
    if item.linked_entity_id:
        raise HTTPException(409, "Gmail radar item is already saved in Life")
    connection = await db.get(GoogleConnection, user["sub"])
    email = connection.email if connection else str(user.get("email") or "")
    url = gmail_urls(item.gmail_thread_id, email)["gmail_url"]
    # The existing Life Inbox takes free text (max 1200).
    # AI is NOT called here: only the explicit classify button can trigger it.
    input_text = ("Gmail 通知：" + item.title +
                  ("\n摘要：" + item.summary if item.summary else "") +
                  "\n原信連結：" + url)[:1200]
    return {"id": item.id, "text": input_text,
            "action_id": _handoff_action_id(item.id), "saved": False}


@router.post("/items/{item_id}/confirm-life-link")
async def confirm_gmail_life_inbox_link(
    item_id: str,
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark completed ONLY after Life Inbox has committed a real target receipt."""
    item = await db.scalar(select(GmailRadarItem).where(
        GmailRadarItem.id == item_id, GmailRadarItem.user_sub == user["sub"],
    ))
    if item is None:
        raise HTTPException(404, "Gmail radar item not found")
    if item.linked_target and item.linked_entity_id:
        return {"linked": True, "target": item.linked_target,
                "entity_id": item.linked_entity_id,
                "target_route": _target_route(item.linked_target)}
    receipt = await db.scalar(select(ExecutionLog).where(
        ExecutionLog.user_sub == user["sub"],
        ExecutionLog.action_type == "inbox.create",
        ExecutionLog.action_id == _handoff_action_id(item.id),
        ExecutionLog.status == "success",
    ))
    if receipt is None or not receipt.entity_id:
        raise HTTPException(409, "Life Inbox write not yet confirmed")
    target = "calendar" if receipt.entity_type == "calendar_event" else receipt.entity_type
    if target not in _TARGET_ROUTES:
        raise HTTPException(409, "Life Inbox target is unsupported")
    item.linked_target = target
    item.linked_entity_id = receipt.entity_id
    item.status = "completed"
    await db.commit()
    return {"linked": True, "target": target,
            "entity_id": receipt.entity_id, "target_route": _target_route(target)}


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


async def _list_three_day_ids(db: AsyncSession, sub: str, scope: str):
    """Count actual enumerated message IDs, not Gmail resultSizeEstimate."""
    found: list[str] = []
    unique: set[str] = set()
    page_token: str | None = None
    complete = False
    for _ in range(THREE_DAY_MAX_PAGES):
        params: dict[str, str | int] = {
            "q": THREE_DAY_QUERY, "maxResults": THREE_DAY_PAGE_SIZE,
        }
        if page_token:
            params["pageToken"] = page_token
        res = await _request_google(
            db, sub, scope, "GET", GMAIL_LIST_URL,
            params=params, preserve_transaction=True,
        )
        body = res.json()
        if not isinstance(body, dict):
            raise HTTPException(502, "Gmail returned invalid three-day list")
        for raw in body.get("messages") or []:
            if isinstance(raw, dict) and raw.get("id"):
                message_id = str(raw["id"])
                if message_id not in unique:
                    found.append(message_id)
                    unique.add(message_id)
        page_token = str(body.get("nextPageToken") or "") or None
        if not page_token:
            complete = True
            break
    return found, complete


async def _run_scan(user: dict, db: AsyncSession, *, kind: Literal["quick", "backfill"]):
    sub = user["sub"]
    locked = (await db.execute(
        text("SELECT pg_try_advisory_xact_lock(5623, hashtext(:sub))"),
        {"sub": sub},
    )).scalar_one()
    if not locked:
        raise HTTPException(409, "This account already has a Gmail scan in progress")

    connection = await db.get(GoogleConnection, sub)
    scope = SERVICE_SCOPES["gmail"][0]
    if connection is None or scope not in set(connection.scopes.split()):
        raise HTTPException(409, "Please authorize Gmail in Google service connections")
    now = datetime.now(timezone.utc)
    three_day_ids, listed_all = await _list_three_day_ids(db, sub, scope)

    if kind == "quick":
        response = await _request_google(
            db, sub, scope, "GET", GMAIL_LIST_URL,
            params={"q": QUICK_QUERY, "maxResults": QUICK_LIMIT},
            preserve_transaction=True,
        )
        body = response.json()
        if not isinstance(body, dict):
            raise HTTPException(502, "Gmail returned invalid quick scan list")
        selected = [
            str(ref["id"]) for ref in body.get("messages") or []
            if isinstance(ref, dict) and ref.get("id")
        ][:QUICK_LIMIT]
    else:
        selected = []

    lookup_ids = list(dict.fromkeys([*three_day_ids, *selected]))
    seen_ids: set[str] = set()
    if lookup_ids:
        result = await db.execute(select(GmailRadarSeen.gmail_message_id).where(
            GmailRadarSeen.user_sub == sub,
            GmailRadarSeen.gmail_message_id.in_(lookup_ids),
        ))
        seen_ids = set(result.scalars().all())

    if kind == "backfill":
        # Only unseen IDs, not the first 40 IDs again. Repeating backfill
        # thus progresses through three days rather than wasting requests.
        selected = [message_id for message_id in three_day_ids
                    if message_id not in seen_ids][:BACKFILL_BATCH]
    checked, added, skipped, failed = 0, 0, 0, 0
    newly_seen: set[str] = set()
    for message_id in selected:
        checked += 1
        if message_id in seen_ids or message_id in newly_seen:
            skipped += 1
            continue
        existing = await db.scalar(select(GmailRadarItem.id).where(
            GmailRadarItem.user_sub == sub,
            GmailRadarItem.gmail_message_id == message_id,
        ))
        if existing:
            skipped += 1
            db.add(GmailRadarSeen(user_sub=sub, gmail_message_id=message_id,
                                 checked_at=now))
            newly_seen.add(message_id)
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
            if not isinstance(raw, dict):
                raise ValueError("Invalid Gmail metadata")
            subject = _gmail_header(raw, "Subject").strip()[:500]
            snippet = str(raw.get("snippet") or "").strip()[:500]
            category = classify_message(subject, snippet)
            if category:
                stamp = raw.get("internalDate")
                received_at = None
                if stamp is not None:
                    try:
                        received_at = datetime.fromtimestamp(
                            int(stamp) / 1000, tz=timezone.utc)
                    except (ValueError, TypeError, OverflowError):
                        pass
                db.add(GmailRadarItem(
                    user_sub=sub, gmail_message_id=message_id,
                    gmail_thread_id=str(raw.get("threadId") or message_id),
                    category=category, title=subject or "Gmail 待確認事項",
                    summary=snippet[:320], sender=_gmail_header(raw, "From")[:320],
                    status="pending", received_at=received_at,
                ))
                added += 1
            else:
                skipped += 1
            db.add(GmailRadarSeen(user_sub=sub, gmail_message_id=message_id,
                                 checked_at=now))
            newly_seen.add(message_id)
        except HTTPException as exc:
            if exc.status_code in (401, 403, 409):
                raise
            failed += 1
        except (ValueError, TypeError, KeyError):
            failed += 1

    covered_ids = seen_ids | newly_seen
    remaining = sum(message_id not in covered_ids for message_id in three_day_ids)
    three_day_complete = listed_all and remaining == 0
    state = await db.get(GmailRadarScanState, sub)
    if state is None:
        state = GmailRadarScanState(user_sub=sub, status="succeeded")
        db.add(state)
    state.status = "partial" if failed or not listed_all else "succeeded"
    state.last_started_at = now
    state.last_finished_at = datetime.now(timezone.utc)
    state.scan_kind = kind
    state.checked, state.added, state.skipped, state.failed = checked, added, skipped, failed
    state.three_day_count = len(three_day_ids)
    state.three_day_remaining = remaining
    state.three_day_complete = three_day_complete
    await db.commit()
    return {
        "source": "rules", "scan_window_days": 7 if kind == "quick" else 3,
        "limit": QUICK_LIMIT if kind == "quick" else BACKFILL_BATCH,
        "three_day_count_capped": not listed_all,
        **_serialize_state(state),
    }


@router.post("/quick-scan")
async def manual_quick_scan(
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    return await _run_scan(user, db, kind="quick")


@router.post("/backfill-three-days")
async def manual_three_day_backfill(
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explicit per-user button only; bounded 40 unseen IDs per request."""
    return await _run_scan(user, db, kind="backfill")
