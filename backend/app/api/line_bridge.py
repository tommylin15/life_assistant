"""LINE OA thin adapter: verified webhook, account binding, drafts and scoped reads.

No LINE request writes directly to Tasks, Shopping, Calendar or Notes.
A draft becomes a Life item only through the existing explicit-confirmation flow.
"""
import base64
import hashlib
import hmac
import logging
import os
import re
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import auth
from app.api.auth import current_user
from app.db.session import get_db
from app.models.line_bridge import LineAccountLink, LineCaptureDraft
from app.models.shopping import ShoppingList
from app.models.task import Task

router = APIRouter(prefix="/line", tags=["line-bridge"])
log = logging.getLogger(__name__)
_LINE_USER = re.compile(r"^U[0-9a-f]{32}$")


class LineIdentity(BaseModel):
    id_token: str = Field(min_length=20, max_length=8192)


def _config():
    enabled = os.getenv("LINE_BRIDGE_ENABLED", "false").lower() == "true"
    audience = os.getenv("LINE_BRIDGE_AUDIENCE", "")
    channel_id = os.getenv("LINE_LOGIN_CHANNEL_ID", "")
    if not enabled or audience not in ("production", "staging") or not channel_id:
        raise HTTPException(503, "LINE integration is not configured")
    return audience, channel_id


def valid_webhook_signature(raw: bytes, signature: str, secret: str) -> bool:
    """Verify exact raw request bytes, before parsing JSON."""
    if not secret or not signature or len(signature) > 120:
        return False
    digest = base64.b64encode(hmac.new(
        secret.encode("utf-8"), raw, hashlib.sha256
    ).digest()).decode("ascii")
    return hmac.compare_digest(digest, signature)


async def _verified_line_user(id_token: str) -> str:
    _, client_id = _config()
    if not id_token:
        raise HTTPException(401, "LINE sign-in required")
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                "https://api.line.me/oauth2/v2.1/verify",
                data={"id_token": id_token, "client_id": client_id},
            )
    except httpx.HTTPError as exc:
        log.warning("line_token_verification_unavailable category=%s", type(exc).__name__)
        raise HTTPException(503, "LINE identity service unavailable") from None
    if response.status_code != 200:
        raise HTTPException(401, "Invalid LINE identity")
    try:
        claims = response.json()
        sub = claims.get("sub", "")
        expected = claims.get("aud")
        expiry = int(claims.get("exp", 0))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(401, "Invalid LINE identity") from None
    if not isinstance(sub, str) or not _LINE_USER.fullmatch(sub):
        raise HTTPException(401, "Unsupported LINE identity")
    if expected != client_id or expiry <= int(datetime.now(timezone.utc).timestamp()):
        raise HTTPException(401, "Expired or mismatched LINE identity")
    if claims.get("iss") != "https://access.line.me":
        raise HTTPException(401, "Invalid LINE token issuer")
    return sub


async def _bearer_user(authorization: str | None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "LINE ID token required")
    return await _verified_line_user(authorization[7:].strip())


async def _linked_user(db: AsyncSession, line_user_id: str) -> tuple[str, str]:
    audience, _ = _config()
    row = await db.get(LineAccountLink, (line_user_id, audience))
    if row is None or row.revoked_at is not None:
        raise HTTPException(403, "Bind your LINE account to Life first")
    return row.user_sub, audience


def _check_google_audience(request: Request, audience: str) -> None:
    actual = "staging" if auth._fixed_staging_origin(request) else "production"
    if audience != actual:
        raise HTTPException(403, "LINE and Life environments must match")


@router.get("/config")
async def line_config():
    # LIFF ID is public; never expose the channel secret or access token.
    audience, _ = _config()
    liff_id = os.getenv("LINE_LIFF_ID", "")
    return {"enabled": True, "liff_id": liff_id, "audience": audience}


@router.post("/bind")
async def bind_line(
    request: Request, body: LineIdentity,
    user: dict = Depends(current_user), db: AsyncSession = Depends(get_db),
):
    audience, _ = _config()
    _check_google_audience(request, audience)
    line_user_id = await _verified_line_user(body.id_token)
    row = await db.get(LineAccountLink, (line_user_id, audience))
    if row and row.revoked_at is None and row.user_sub != user["sub"]:
        raise HTTPException(409, "LINE identity is already linked to another Life account")
    if row:
        row.user_sub = user["sub"]
        row.revoked_at = None
    else:
        db.add(LineAccountLink(
            line_user_id=line_user_id, audience=audience, user_sub=user["sub"]
        ))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "LINE link conflict") from None
    return {"linked": True, "audience": audience}


@router.post("/unbind")
async def unbind_line(
    request: Request, body: LineIdentity,
    user: dict = Depends(current_user), db: AsyncSession = Depends(get_db),
):
    audience, _ = _config()
    _check_google_audience(request, audience)
    line_user_id = await _verified_line_user(body.id_token)
    row = await db.get(LineAccountLink, (line_user_id, audience))
    if row is None or row.revoked_at is not None or row.user_sub != user["sub"]:
        raise HTTPException(404, "LINE link not found")
    row.revoked_at = datetime.now(timezone.utc)
    await db.commit()
    return {"linked": False}


@router.get("/me")
async def line_me(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    line_id = await _bearer_user(authorization)
    sub, audience = await _linked_user(db, line_id)
    return {"linked": True, "audience": audience, "has_account": bool(sub)}


@router.get("/drafts")
async def line_drafts(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    line_id = await _bearer_user(authorization)
    sub, audience = await _linked_user(db, line_id)
    rows = (await db.execute(
        select(LineCaptureDraft).where(
            LineCaptureDraft.line_user_id == line_id,
            LineCaptureDraft.audience == audience,
            LineCaptureDraft.user_sub == sub,
        ).order_by(LineCaptureDraft.received_at.desc()).limit(20)
    )).scalars().all()
    return {"drafts": [{
        "message_id": row.message_id, "text": row.body,
        "received_at": row.received_at.isoformat(),
    } for row in rows]}


@router.get("/summary")
async def line_summary(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    line_id = await _bearer_user(authorization)
    sub, _ = await _linked_user(db, line_id)
    tasks = (await db.execute(select(Task).where(
        Task.user_sub == sub, Task.deleted_at.is_(None),
        Task.status.notin_(["completed", "cancelled"]),
    ).order_by(Task.due_at.asc().nullslast()).limit(5))).scalars().all()
    shopping = (await db.execute(select(ShoppingList).where(
        ShoppingList.user_sub == sub
    ).order_by(ShoppingList.created_at.desc()).limit(5))).scalars().all()
    return {"tasks": [{"title": t.title, "due_at": t.due_at.isoformat() if t.due_at else None}
                      for t in tasks],
            "shopping_lists": [{"name": s.name} for s in shopping],
            "note": "Only Life PostgreSQL tasks and shopping list names are shown; external Google Calendar is not queried."}


async def _reply(reply_token: str | None, text: str) -> None:
    access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not access_token or not reply_token:
        return
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                "https://api.line.me/v2/bot/message/reply",
                headers={"Authorization": f"Bearer {access_token}"},
                json={"replyToken": reply_token,
                      "messages": [{"type": "text", "text": text[:500]}]},
            )
        if response.status_code >= 400:
            log.warning("line_reply_failed http_status=%d", response.status_code)
    except httpx.HTTPError as exc:
        log.warning("line_reply_unavailable category=%s", type(exc).__name__)


@router.post("/webhook")
async def line_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    audience, _ = _config()
    secret = os.getenv("LINE_CHANNEL_SECRET", "")
    raw = await request.body()
    if len(raw) > 65536:
        raise HTTPException(413, "Webhook too large")
    if not valid_webhook_signature(raw, request.headers.get("x-line-signature", ""), secret):
        raise HTTPException(401, "Invalid LINE webhook signature")
    try:
        payload = __import__("json").loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "Malformed webhook") from None
    events = payload.get("events", []) if isinstance(payload, dict) else None
    if not isinstance(events, list) or len(events) > 50:
        raise HTTPException(400, "Invalid webhook events")
    processed = 0
    for event in events:
        if not isinstance(event, dict) or event.get("type") != "message":
            continue
        source = event.get("source") or {}
        message = event.get("message") or {}
        if source.get("type") != "user" or message.get("type") != "text":
            continue  # No group or room messages; never infer an account from those.
        line_user_id = source.get("userId", "")
        message_id = message.get("id", "")
        body = message.get("text", "")
        if not isinstance(line_user_id, str) or not _LINE_USER.fullmatch(line_user_id):
            continue
        if not isinstance(message_id, str) or not 1 <= len(message_id) <= 128:
            continue
        if not isinstance(body, str) or not 1 <= len(body) <= 1200:
            await _reply(event.get("replyToken"), "請改用 1,200 字以內的文字記錄。")
            continue
        existing = await db.get(LineCaptureDraft, message_id)
        if existing is not None:
            continue  # Stable LINE message ID: redelivery must not duplicate.
        link = await db.get(LineAccountLink, (line_user_id, audience))
        if link is None or link.revoked_at is not None:
            await _reply(event.get("replyToken"), "請先從 Life LINE 選單完成帳號綁定，才能保存個人記錄。")
            continue
        try:
            sent_ms = int(event.get("timestamp", 0))
            received = datetime.fromtimestamp(sent_ms / 1000, timezone.utc)
            if sent_ms <= 0:
                raise ValueError("missing timestamp")
        except (TypeError, ValueError, OverflowError):
            continue  # Never invent a relative-date anchor.
        db.add(LineCaptureDraft(
            message_id=message_id, line_user_id=line_user_id, user_sub=link.user_sub,
            audience=audience, body=body, received_at=received,
        ))
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            continue  # Concurrent redelivery won the unique message ID race.
        processed += 1
        await _reply(event.get("replyToken"), "已存入 Life 快速記錄草稿；請在選單確認分類後再正式建立事項。")
    return {"ok": True, "created": processed}
