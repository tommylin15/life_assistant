"""LINE B: durable text capture, scoped lookup, LIFF and two-sided binding."""
import asyncio
import json
import re
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Query
from pydantic import BaseModel, Field, ConfigDict
from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_user, SESSION_COOKIE
from app.api.ui_policies import feature_gate, _audit
from app.db.session import get_db
from app.models.line import LineBinding, LineLinkTicket, LineSession, LineEvent
from app.models.note import Note
from app.models.task import Task
from app.models.shopping import ShoppingList, ShoppingItem
from app.services.ownership import visible_clause
from app.services.line_channel import (
    aware, check_origin, configuration, digest, liff_url, reply_message,
    utcnow, verify_id_token, verify_signature,
)

router = APIRouter(prefix="/line", tags=["line"])


class TokenInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id_token: str = Field(min_length=20, max_length=8192)


class TicketInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    code: str = Field(pattern=r"^[A-Za-z0-9_-]{32}$")


async def line_user(user=Depends(current_user), db=Depends(get_db)):
    configuration()
    await feature_gate("line")(user=user, db=db)
    return user


def no_store(response):
    response.headers["Cache-Control"] = "no-store"


def google_only(user):
    if user.get("line_binding_id"):
        raise HTTPException(403, "Use Google login to manage account linking")


@router.get("/config")
async def public_config(response: Response):
    no_store(response)
    cfg = configuration()
    return {"liff_id": cfg["liff_id"], "origin": cfg["origin"]}


@router.post("/session")
async def login(body: TokenInput, request: Request, response: Response,
                db: AsyncSession = Depends(get_db)):
    cfg = configuration()
    check_origin(request, cfg)
    identity = await verify_id_token(body.id_token, cfg)
    binding = await db.scalar(select(LineBinding).where(
        LineBinding.namespace == cfg["namespace"], LineBinding.line_user_id == identity,
        LineBinding.active.is_(True)))
    if binding is None:
        raise HTTPException(409, "請先在 Life 完成 LINE 帳號綁定")
    user = {"sub": binding.user_sub, "email": binding.email, "name": binding.display_name}
    await feature_gate("line")(user=user, db=db)
    bearer = secrets.token_urlsafe(48)
    db.add(LineSession(token_hash=digest(bearer), binding_id=binding.id,
                       expires_at=utcnow() + timedelta(hours=1)))
    await db.commit()
    response.set_cookie(SESSION_COOKIE, "ln:" + bearer, max_age=3600,
                        httponly=True, secure=True, samesite="lax", path="/")
    no_store(response)
    return {"linked": True, "name": binding.display_name}


@router.post("/link/start")
async def start_link(request: Request, response: Response,
                     user: dict = Depends(line_user), db: AsyncSession = Depends(get_db)):
    google_only(user)
    cfg = configuration()
    check_origin(request, cfg)
    # At most one live challenge per Life account; never store the clear code.
    await db.execute(delete(LineLinkTicket).where(
        LineLinkTicket.namespace == cfg["namespace"], LineLinkTicket.user_sub == user["sub"]))
    code = secrets.token_urlsafe(24)
    db.add(LineLinkTicket(token_hash=digest(code), namespace=cfg["namespace"],
                         user_sub=user["sub"], expires_at=utcnow() + timedelta(minutes=10)))
    await db.commit()
    no_store(response)
    return {"code": code, "message": "綁定 " + code, "expires_in": 600}


async def ticket_for(body, user, db):
    google_only(user)
    ticket = await db.scalar(select(LineLinkTicket).where(
        LineLinkTicket.token_hash == digest(body.code),
        LineLinkTicket.namespace == configuration()["namespace"],
        LineLinkTicket.user_sub == user["sub"]).with_for_update())
    if ticket is None or ticket.consumed or aware(ticket.expires_at) <= utcnow():
        raise HTTPException(409, "綁定碼無效或已到期，請重新產生")
    return ticket


@router.post("/link/check")
async def check_link(body: TicketInput, request: Request, response: Response,
                     user: dict = Depends(line_user), db: AsyncSession = Depends(get_db)):
    check_origin(request, configuration())
    ticket = await ticket_for(body, user, db)
    no_store(response)
    return {"ready": bool(ticket.line_user_id),
            "line_suffix": ticket.line_user_id[-6:] if ticket.line_user_id else None}


@router.post("/link/confirm")
async def confirm_link(body: TicketInput, request: Request,
                       user: dict = Depends(line_user), db: AsyncSession = Depends(get_db)):
    cfg = configuration()
    check_origin(request, cfg)
    ticket = await ticket_for(body, user, db)
    if not ticket.line_user_id:
        raise HTTPException(409, "請先從自己的 LINE 傳送綁定碼")
    existing = await db.scalar(select(LineBinding).where(LineBinding.namespace == cfg["namespace"],
        or_(LineBinding.user_sub == user["sub"], LineBinding.line_user_id == ticket.line_user_id)))
    if existing is not None:
        raise HTTPException(409, "帳號已有綁定，請先解除；不會覆蓋其他帳號")
    db.add(LineBinding(id=str(uuid.uuid4()), namespace=cfg["namespace"],
        user_sub=user["sub"], line_user_id=ticket.line_user_id,
        email=user["email"], display_name=user.get("name", ""), active=True))
    ticket.consumed = True
    _audit(db, user["sub"], "line.link", "Confirmed LINE account link")
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, "帳號已有綁定") from None
    return {"linked": True}


@router.get("/link/status")
async def link_status(response: Response, user: dict = Depends(line_user), db: AsyncSession = Depends(get_db)):
    google_only(user)
    no_store(response)
    binding = await db.scalar(select(LineBinding).where(LineBinding.namespace == configuration()["namespace"],
        LineBinding.user_sub == user["sub"]))
    return {"linked": binding is not None, "active": bool(binding and binding.active)}


@router.post("/link/unlink")
async def unlink(request: Request, user: dict = Depends(line_user), db: AsyncSession = Depends(get_db)):
    google_only(user)
    check_origin(request, configuration())
    await db.execute(delete(LineBinding).where(LineBinding.namespace == configuration()["namespace"],
        LineBinding.user_sub == user["sub"]))
    _audit(db, user["sub"], "line.unlink", "Revoked LINE account link")
    await db.commit()  # Every LINE session rechecks binding on every request.
    return {"linked": False}


async def lookup(kind, keyword, user, db, offset=0):
    """Bounded real rows; no LLM-supplied SQL and no invented personal memories."""
    keyword = keyword[:120].strip()
    rows = []
    if kind in ("notes", "tasks", "shopping"):
        await feature_gate(kind)(user=user, db=db)
    if kind == "notes":
        query = select(Note).where(visible_clause(Note, user))
        if keyword:
            query = query.where(or_(Note.title.contains(keyword, autoescape=True),
                                   Note.body.contains(keyword, autoescape=True)))
        items = (await db.scalars(query.order_by(Note.updated_at.desc(), Note.id).offset(offset).limit(21))).all()
        rows = [{"id": n.id, "title": n.title or "未命名筆記", "detail": (n.body or "")[:500],
                 "date": n.updated_at.isoformat(), "kind": "notes"} for n in items]
    elif kind == "tasks":
        query = select(Task).where(visible_clause(Task, user), Task.deleted_at.is_(None),
                                   Task.status.notin_(("completed", "cancelled")))
        if keyword:
            query = query.where(or_(Task.title.contains(keyword, autoescape=True), Task.note.contains(keyword, autoescape=True)))
        items = (await db.scalars(query.order_by(Task.due_at.asc().nullslast(), Task.id).offset(offset).limit(21))).all()
        rows = [{"id": t.id, "title": t.title, "detail": t.note or "", "kind": "tasks",
                 "date": t.due_at.isoformat() if t.due_at else None} for t in items]
    elif kind == "shopping":
        query = select(ShoppingItem, ShoppingList.name).join(ShoppingList).where(
            visible_clause(ShoppingList, user), ShoppingItem.is_done.is_(False))
        if keyword:
            query = query.where(ShoppingItem.name.contains(keyword, autoescape=True))
        items = (await db.execute(query.order_by(ShoppingList.id, ShoppingItem.sort_order, ShoppingItem.id)
                                 .offset(offset).limit(21))).all()
        rows = [{"id": i.id, "title": i.name, "detail": name, "kind": "shopping"} for i, name in items]
    return {"items": rows[:20], "has_more": len(rows) > 20, "offset": offset}


@router.get("/search")
async def search(response: Response, kind: Literal["notes", "tasks", "shopping"] = "notes",
                 q: str = Query("", max_length=120), offset: int = Query(0, ge=0, le=10000),
                 user: dict = Depends(line_user), db: AsyncSession = Depends(get_db)):
    no_store(response)
    return await lookup(kind, q, user, db, offset)


@router.get("/drafts")
async def drafts(response: Response, user: dict = Depends(line_user), db: AsyncSession = Depends(get_db)):
    await feature_gate("life_inbox")(user=user, db=db)
    no_store(response)
    rows = (await db.scalars(select(LineEvent).where(
        LineEvent.namespace == configuration()["namespace"], LineEvent.user_sub == user["sub"],
        LineEvent.expires_at > utcnow(), LineEvent.text != "").order_by(LineEvent.created_at.desc()).limit(30))).all()
    return {"items": [{"id": r.id, "text": r.text, "created_at": r.created_at.isoformat()} for r in rows]}


@router.get("/drafts/{event_id}")
async def draft(event_id: str, response: Response, user: dict = Depends(line_user), db: AsyncSession = Depends(get_db)):
    await feature_gate("life_inbox")(user=user, db=db)
    no_store(response)
    row = await db.get(LineEvent, event_id)
    if (row is None or row.user_sub != user["sub"] or row.namespace != configuration()["namespace"]
            or aware(row.expires_at) <= utcnow() or not row.text):
        raise HTTPException(404, "草稿不存在或已到期")
    return {"id": row.id, "text": row.text, "created_at": row.created_at.isoformat()}


@router.post("/drafts/{event_id}/archive")
async def archive_draft(event_id: str, request: Request, user: dict = Depends(line_user),
                        db: AsyncSession = Depends(get_db)):
    check_origin(request, configuration())
    row = await db.get(LineEvent, event_id)
    if row is None or row.user_sub != user["sub"] or row.namespace != configuration()["namespace"]:
        raise HTTPException(404, "Draft not found")
    row.text = ""  # Keep the deduplication receipt, remove only the raw draft.
    _audit(db, user["sub"], "line.draft.archive", "Removed LINE draft text")
    await db.commit()
    return {"archived": True}


async def cleanup_expired(db):
    # Bounded opportunistic maintenance; no permanent in-process scheduler.
    for model, key in ((LineEvent, LineEvent.id), (LineSession, LineSession.token_hash),
                       (LineLinkTicket, LineLinkTicket.token_hash)):
        expired = (await db.scalars(select(key).where(model.expires_at < utcnow()).limit(100))).all()
        if expired:
            await db.execute(delete(model).where(key.in_(expired)))
    await db.commit()


def message(text, cfg, page="capture", **params):
    return [{"type": "text", "text": text[:4500], "quickReply": {"items": [
        {"type": "action", "action": {"type": "uri", "label": "開啟 Life", "uri": liff_url(cfg, page=page, **params)}}]}}]


async def build_reply(event, record, identity, cfg, db):
    text_value = str((event.get("message") or {}).get("text", "")).strip()
    match = re.fullmatch(r"綁定\s+([A-Za-z0-9_-]{32})", text_value)
    if match:
        ticket = await db.scalar(select(LineLinkTicket).where(
            LineLinkTicket.token_hash == digest(match[1]), LineLinkTicket.namespace == cfg["namespace"]).with_for_update())
        if ticket is None or ticket.consumed or aware(ticket.expires_at) <= utcnow():
            return message("綁定碼無效或到期。請在 Life 重新產生。", cfg)
        if ticket.line_user_id and ticket.line_user_id != identity:
            return message("綁定碼已被使用，請重新產生。", cfg)
        ticket.line_user_id = identity
        return message("已收到綁定申請。請回到 Life 確認帳號尾碼：" + identity[-6:] + "。確認後再開啟助手。", cfg)
    binding = await db.scalar(select(LineBinding).where(LineBinding.namespace == cfg["namespace"],
        LineBinding.line_user_id == identity))
    if event.get("type") == "unfollow":
        if binding:
            binding.active = False
        return []
    if binding is None or not binding.active:
        return message("請先用外部瀏覽器登入 Life，完成帳號綁定：\n" + cfg["origin"] + "/line/link.html", cfg)
    user = {"sub": binding.user_sub, "email": binding.email, "name": binding.display_name}
    await feature_gate("line")(user=user, db=db)
    record.binding_id, record.user_sub = binding.id, binding.user_sub
    if event.get("type") == "follow":
        return message("歡迎使用 Life。直接傳文字可保留草稿；輸入「查 筆記 關鍵字」、「待辦」或「購物」查詢。", cfg)
    if event.get("type") == "postback":
        # LINE v2 is additive: signed, actor-scoped postbacks reuse the existing
        # v1 binding, rollout gate, event receipt and reply deduplication.
        from app.services.line_v2 import handle_postback
        return await handle_postback(event, identity, cfg, user, db)
    # V2-01 can be tested through the existing six-cell OA without replacing
    # Rich Menu. Only exact, reserved chat commands enter the activity flow.
    chat_events = {"活動": "events.latest", "最新活動": "events.latest",
                   "活動分類": "events.tags", "已收藏活動": "events.saved"}
    if event.get("type") == "message" and text_value in chat_events:
        from app.services.line_v2 import handle_postback
        return await handle_postback(
            {"postback": {"data": "v=2&cmd=" + chat_events[text_value]}},
            identity, cfg, user, db)
    if event.get("type") != "message" or (event.get("message") or {}).get("type") != "text":
        return message("目前支援文字與網址。圖片、語音請先轉成文字；尚未建立任何事項。", cfg)
    menus = {"快速記錄": "capture", "今日總覽": "today", "查我的資料": "search",
             "待辦・購物": "tasks", "日曆・活動": "calendar", "我的 Life": "home"}
    if text_value in menus:
        return message("開啟「" + text_value + "」。", cfg, menus[text_value])
    kinds = {"筆記": "notes", "待辦": "tasks", "購物": "shopping"}
    query = re.fullmatch(r"(?:查|查詢)\s*(筆記|待辦|購物)\s*(.*)", text_value)
    if query or text_value in ("待辦", "購物"):
        kind = kinds[query[1] if query else text_value]
        result = await lookup(kind, query[2] if query else "", user, db)
        lines = [f"• {r['title']}" + (f"（{r['date']}）" if r.get("date") else "") for r in result["items"][:5]]
        return message("\n".join(lines) if lines else "找不到符合條件的記錄。", cfg, "search", kind=kind, q=query[2] if query else "")
    if (text_value.endswith(("?", "？")) or text_value.startswith(("查", "找", "搜尋"))
            or re.search(r"什麼|哪些|有沒有|在哪|何時|幾點|嗎$", text_value)):
        return message("請選擇資料類型與關鍵字查詢，例如「查 筆記 水電」。這則詢問沒有存成草稿。", cfg, "search")
    await feature_gate("life_inbox")(user=user, db=db)
    if not text_value or len(text_value) > 1200:
        return message("請使用 1–1200 字的文字；本則尚未儲存，請分段傳送。", cfg)
    record.text = text_value
    from app.services.line_capture import begin_capture
    return await begin_capture(text_value, record, identity, cfg, user, db)


@router.post("/webhook")
async def webhook(request: Request, db: AsyncSession = Depends(get_db)):
    cfg = configuration()
    raw = bytearray()
    async for chunk in request.stream():
        raw.extend(chunk)
        if len(raw) > 256000:
            raise HTTPException(413, "Webhook too large")
    verify_signature(bytes(raw), request.headers.get("x-line-signature", ""), cfg["channel_secret"])
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "Invalid webhook") from None
    events = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(events, list) or len(events) > 100:
        raise HTTPException(400, "Invalid webhook events")
    await cleanup_expired(db)
    for event in events:
        if not isinstance(event, dict):
            continue
        source = event.get("source") or {}
        # Never return private information or capture group messages.
        if source.get("type") != "user" or not re.fullmatch(r"U[0-9a-f]{32}", str(source.get("userId", ""))):
            continue
        event_id = event.get("webhookEventId")
        if not isinstance(event_id, str) or not 1 <= len(event_id) <= 128:
            raise HTTPException(400, "Missing event identity")
        key = digest(cfg["namespace"] + ":" + event_id)
        record = await db.get(LineEvent, key)
        if record is None:
            try:
                timestamp = event.get("timestamp")
                captured_at = datetime.fromtimestamp(timestamp / 1000, timezone.utc) if isinstance(timestamp, (int, float)) else utcnow()
            except (ValueError, OverflowError, OSError):
                raise HTTPException(400, "Invalid event timestamp") from None
            if captured_at < utcnow() - timedelta(days=30):
                continue  # Expired redeliveries cannot resurrect deleted drafts.
            record = LineEvent(id=key, namespace=cfg["namespace"], created_at=captured_at,
                               expires_at=utcnow() + timedelta(days=30), text="", reply=[])
            db.add(record)
            try:
                await db.commit()
            except IntegrityError:
                await db.rollback()  # Another instance accepted the same event.
        record = await db.scalar(select(LineEvent).where(LineEvent.id == key).with_for_update())
        if record.reply_sent:
            await db.rollback()
            continue
        if not record.reply:
            try:
                record.reply = await asyncio.wait_for(build_reply(event, record, source["userId"], cfg, db), timeout=8)
            except HTTPException as exc:
                if exc.status_code not in (403, 503):
                    raise
                record.reply = message("此功能目前未開放，請至 Life 查看設定。", cfg, "home")
            await db.commit()  # Durable draft/result before attempting external reply.
        token = event.get("replyToken")
        if record.reply and isinstance(token, str) and token:
            await reply_message(token, record.reply, cfg)
        record.reply_sent = True
        await db.commit()
    return {"received": True}
