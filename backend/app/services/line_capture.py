"""Conversation-native LINE capture with explicit, idempotent Life confirmation."""
import re
import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import inbox
from app.api.ui_policies import feature_gate
from app.models.line_capture import LineCapture
from app.models.shopping import ShoppingList
from app.services.ownership import visible_clause
from app.services.line_channel import aware

TAIPEI = ZoneInfo("Asia/Taipei")
SESSION_TTL = timedelta(hours=24)
TYPES = {"shopping": "購物", "task": "待辦", "calendar": "行程", "note": "筆記"}
EDIT_FIELDS = {"title", "body", "note", "category"}
DATETIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$")


def _reply(text, actions, quick_reply):
    # A rendered LINE Flex bubble, not an HTML/LIFF form.
    return [{"type": "flex", "altText": "Life 智慧記錄",
             "contents": {"type": "bubble", "body": {"type": "box",
                 "layout": "vertical", "spacing": "md", "contents": [
                     {"type": "text", "text": "Life 智慧記錄", "size": "lg", "weight": "bold"},
                     {"type": "text", "text": text[:1500], "size": "sm", "wrap": True}
                 ]}},
             "quickReply": quick_reply(actions)}]


def _controls(session, cfg, user, identity, make_token, postback_action):
    def button(label, cmd, **extra):
        return postback_action(label, make_token(
            cfg, user, identity, cmd, i=session.id, r=session.revision, **extra))
    return button


def _direct(cfg, path, label="到 Life 完整編輯"):
    return {"type": "uri", "label": label, "uri": cfg["origin"] + path}


def _suggest(text, when):
    proposals = inbox.rule_candidates(text, when)
    candidates = proposals.get("candidates", []) if proposals else []
    if len(candidates) == 1 and candidates[0].get("target") in TYPES:
        return candidates[0]
    return None


async def _owner_session(db, sid, identity, cfg, user):
    if not isinstance(sid, str) or not re.fullmatch(r"[0-9a-f-]{36}", sid):
        return None
    session = await db.scalar(select(LineCapture).where(LineCapture.id == sid).with_for_update())
    if (session is None or session.namespace != cfg["namespace"] or
        session.line_user_id != identity or session.user_sub != user["sub"] or
        aware(session.expires_at) <= datetime.now(timezone.utc)):
        return None
    return session


def _preview(session, cfg, user, identity, make_token, postback_action, quick_reply):
    button = _controls(session, cfg, user, identity, make_token, postback_action)
    if session.status == "confirmed":
        return _reply("已確認新增至 Life。請到相應頁面查看實際資料。", [
            _direct(cfg, {"shopping": "/more/shopping", "task": "/tasks",
                         "calendar": "/calendar", "note": "/more/notes"}[session.target])
        ], quick_reply)
    if session.status in ("submitting", "unknown"):
        return _reply("結果待確認；請查詢既有寫入回執，不要重新新增。", [
            button("查詢回執", "capture.receipt")
        ], quick_reply)
    if session.status == "cancelled":
        return _reply("已取消；沒有正式新增 Life 資料。", [], quick_reply)
    if not session.target:
        suggestion = _suggest(session.source_text, session.created_at.astimezone(TAIPEI).isoformat())
        proposed = suggestion["target"] if suggestion else ("shopping" if len(session.source_text) < 30 else None)
        actions = [button(TYPES[t] + ("（建議）" if t == proposed else ""),
                          "capture.kind", k=t)
                   for t in ("shopping", "task", "calendar", "note")]
        actions.append(button("取消", "capture.cancel"))
        note = ("偵測到多項可能的事項；請分次傳送、逐筆確認。\n"
                if inbox.rule_candidates(session.source_text, session.created_at.astimezone(TAIPEI).isoformat()) and
                len(inbox.rule_candidates(session.source_text, session.created_at.astimezone(TAIPEI).isoformat())["candidates"]) > 1 else "")
        return _reply(note + "「" + session.source_text[:100] +
                      "」\n要新增到哪裡？不會自動儲存。", actions, quick_reply)

    f = session.fields or {}
    if session.target == "shopping":
        entries = f.get("items") or []
        names = "、".join(x.get("name", "") for x in entries if isinstance(x, dict))
        summary = "購物品項：" + (names or "待填") + "\n購物清單：" + (f.get("list_name") or "尚未選擇")
        summary += "\n分類：" + (entries[0].get("category") if entries and entries[0].get("category") else "未指定")
        actions = [button("選購物清單", "capture.list"), button("改分類", "capture.edit", k="category")]
        ready = bool(f.get("shopping_list_id"))
        path = "/more/shopping"
    elif session.target == "task":
        summary = "待辦：" + str(f.get("title") or "") + "\n截止：" + str(f.get("due_at") or "未指定")
        summary += "\n備註：" + str(f.get("note") or "未指定")[:120]
        actions = [button("改標題", "capture.edit", k="title"),
                   {"type": "datetimepicker", "label": "設定截止", "data": make_token(
                       cfg, user, identity, "capture.due", i=session.id, r=session.revision),
                    "mode": "datetime"},
                   button("改備註", "capture.edit", k="note")]
        ready = bool(f.get("title"))
        path = "/tasks"
    elif session.target == "calendar":
        summary = "行程：" + str(f.get("summary") or "") + "\n開始：" + str(f.get("start") or "尚未設定")
        summary += "\n結束：" + str(f.get("end") or "尚未設定")
        actions = [button("改標題", "capture.edit", k="title"),
                   {"type": "datetimepicker", "label": "選開始時間", "data": make_token(
                       cfg, user, identity, "capture.start_at", i=session.id, r=session.revision),
                    "mode": "datetime"},
                   {"type": "datetimepicker", "label": "選結束時間", "data": make_token(
                       cfg, user, identity, "capture.end_at", i=session.id, r=session.revision),
                    "mode": "datetime"}]
        ready = bool(f.get("summary") and f.get("start") and f.get("end"))
        if ready:
            ready = datetime.fromisoformat(f["end"]) > datetime.fromisoformat(f["start"])
        path = "/calendar"
    else:
        summary = "筆記標題：" + str(f.get("title") or "")[:80]
        summary += "\n內容：" + str(f.get("body") or "")[:180]
        summary += "\n分類：" + str(f.get("category") or "未指定")
        actions = [button("改標題", "capture.edit", k="title"),
                   button("改內容", "capture.edit", k="body"),
                   button("改分類", "capture.edit", k="category")]
        ready = bool(f.get("body"))
        path = "/more/notes"
    if ready:
        actions.append(button("確認新增", "capture.confirm"))
    actions += [button("改類型", "capture.preview"), button("取消", "capture.cancel"),
                _direct(cfg, path)]
    return _reply("類型：" + TYPES[session.target] + "\n" + summary +
                  ("\n\n欄位齊全，確認後才會新增。" if ready else
                   "\n\n請補齊必要欄位。"), actions, quick_reply)


async def begin_capture(text, record, identity, cfg, user, db: AsyncSession):
    """Start a new action or consume the requested free-text field edit."""
    from app.services.line_v2 import make_token, postback_action, quick_reply
    now = datetime.now(timezone.utc)
    awaiting = await db.scalar(select(LineCapture).where(
        LineCapture.namespace == cfg["namespace"],
        LineCapture.line_user_id == identity, LineCapture.user_sub == user["sub"],
        LineCapture.status == "pending", LineCapture.awaiting.is_not(None),
        LineCapture.expires_at > now
    ).order_by(LineCapture.created_at.desc()).limit(1).with_for_update())
    if awaiting:
        field = awaiting.awaiting
        value = text.strip()
        if field in EDIT_FIELDS and value:
            f = dict(awaiting.fields or {})
            if field == "title":
                f["summary" if awaiting.target == "calendar" else "title"] = value[:500]
            elif field == "body":
                f["body"] = value[:5000]
            elif field == "note":
                f["note"] = value[:5000]
            elif field == "category" and awaiting.target == "shopping":
                entries = [dict(e) for e in f.get("items") or []]
                for entry in entries:
                    entry["category"] = value[:255]
                f["items"] = entries
            elif field == "category":
                f["category"] = value[:80]
            awaiting.fields, awaiting.awaiting = f, None
            awaiting.revision += 1
            return _preview(awaiting, cfg, user, identity, make_token, postback_action, quick_reply)
    session = LineCapture(
        id=str(uuid.uuid4()), namespace=cfg["namespace"], line_user_id=identity,
        user_sub=user["sub"], source_event_id=record.id, source_text=text[:1200],
        target=None, fields={}, awaiting=None, status="pending", revision=0,
        created_at=record.created_at, expires_at=now + SESSION_TTL)
    db.add(session)
    await db.flush()
    return _preview(session, cfg, user, identity, make_token, postback_action, quick_reply)


async def handle_capture_postback(event, command, identity, cfg, user, db: AsyncSession,
                                  make_token, postback_action, quick_reply):
    await feature_gate("life_inbox")(user=user, db=db)
    session = await _owner_session(db, command.get("i"), identity, cfg, user)
    if session is None:
        return _reply("此卡片已過期或不屬於目前帳號，請重新輸入內容。", [], quick_reply)
    cmd = command["a"]
    if cmd == "capture.receipt" and session.status in ("unknown", "submitting", "confirmed"):
        try:
            receipt = await inbox.receipt("line.capture." + session.id, Response(), user=user, db=db)
            if receipt["status"] == "CREATED":
                session.status = "confirmed"
        except Exception:
            pass
        return _preview(session, cfg, user, identity, make_token, postback_action, quick_reply)
    if session.status != "pending":
        return _preview(session, cfg, user, identity, make_token, postback_action, quick_reply)
    if command.get("r") != session.revision:
        return _reply("卡片內容已有更新，請使用最新卡片繼續。", [], quick_reply)
    if cmd == "capture.cancel":
        session.status, session.awaiting = "cancelled", None
    elif cmd == "capture.preview":
        session.target, session.fields, session.awaiting = None, {}, None
        session.revision += 1
    elif cmd == "capture.kind" and command.get("k") in TYPES:
        kind = command["k"]
        proposal = _suggest(session.source_text, session.created_at.astimezone(TAIPEI).isoformat())
        f = dict(proposal.get("fields") or {}) if proposal and proposal["target"] == kind else {}
        source = session.source_text.strip()
        if kind == "shopping":
            f = {"items": f.get("items") or [{"name": source[:80]}]}
        elif kind == "task":
            f = {"title": f.get("title") or source[:500], "due_at": f.get("due_at")}
        elif kind == "calendar":
            f = {"summary": f.get("summary") or source[:500],
                 "start": f.get("start"), "end": f.get("end")}
        elif kind == "note":
            f = {"title": source[:100], "body": source[:5000]}
        session.target, session.fields, session.awaiting = kind, f, None
        session.revision += 1
    elif cmd == "capture.edit" and command.get("k") in EDIT_FIELDS:
        name = command["k"]
        if name == "note" and session.target != "task":
            return _reply("編輯欄位無效，請重新開啟卡片。", [], quick_reply)
        if name == "body" and session.target != "note":
            return _reply("編輯欄位無效，請重新開啟卡片。", [], quick_reply)
        session.awaiting = name
        session.revision += 1
        return _reply("請直接輸入新的" + {"title":"標題","body":"內容","note":"備註","category":"分類"}[name] +
                      "，下一則訊息會更新目前卡片，不會立即新增 Life 資料。",
                      [postback_action("取消", make_token(cfg, user, identity, "capture.cancel",
                                                       i=session.id, r=session.revision))], quick_reply)
    elif cmd == "capture.list" and session.target == "shopping":
        await feature_gate("shopping")(user=user, db=db)
        lists = (await db.scalars(select(ShoppingList).where(
            visible_clause(ShoppingList, user)).order_by(ShoppingList.created_at.desc()).limit(8))).all()
        button = _controls(session, cfg, user, identity, make_token, postback_action)
        if not lists:
            return _reply("尚無購物清單；請先到 Life 建立一份清單。", [
                _direct(cfg, "/more/shopping", "建立購物清單")], quick_reply)
        return _reply("選擇要加入的購物清單：", [
            button(v.name[:20], "capture.pick_list", k=v.id) for v in lists] +
            [button("返回卡片", "capture.list")], quick_reply)
    elif cmd == "capture.pick_list" and session.target == "shopping":
        await feature_gate("shopping")(user=user, db=db)
        list_id = command.get("k")
        selected = await db.scalar(select(ShoppingList).where(
            ShoppingList.id == list_id, visible_clause(ShoppingList, user)))
        if selected is None:
            return _reply("購物清單不存在或不屬於目前帳號。", [], quick_reply)
        session.fields = {**session.fields, "shopping_list_id": selected.id,
                          "list_name": selected.name}
        session.revision += 1
    elif cmd in ("capture.due", "capture.start_at", "capture.end_at"):
        value = (event.get("postback") or {}).get("params", {}).get("datetime")
        if not isinstance(value, str) or not DATETIME_PATTERN.fullmatch(value):
            return _reply("請使用 LINE 的日期時間選擇器。", [], quick_reply)
        try:
            selected = datetime.fromisoformat(value).replace(tzinfo=TAIPEI)
            iso = selected.isoformat()
        except ValueError:
            return _reply("時間格式無效，請重新選擇。", [], quick_reply)
        allowed = {"capture.due": ("task", "due_at"),
                   "capture.start_at": ("calendar", "start"),
                   "capture.end_at": ("calendar", "end")}
        kind, field = allowed[cmd]
        if session.target != kind:
            return _reply("此日期按鈕與目前類型不符。", [], quick_reply)
        session.fields = {**session.fields, field: iso}
        session.revision += 1
    elif cmd == "capture.confirm":
        target = session.target
        fields = {key: value for key, value in (session.fields or {}).items() if key != "list_name"}
        if target == "shopping" and not fields.get("shopping_list_id"):
            return _reply("請先選擇本人購物清單。", [], quick_reply)
        if target == "calendar" and (not fields.get("start") or not fields.get("end") or
            datetime.fromisoformat(fields["end"]) <= datetime.fromisoformat(fields["start"])):
            return _reply("請先設定有效的行程開始與結束時間。", [], quick_reply)
        if target not in TYPES:
            return _reply("請先選擇類型。", [], quick_reply)
        session.status = "submitting"
        await db.commit()  # Persist decision BEFORE any external Calendar effect.
        result = await inbox.commit(inbox.ConfirmBatch(items=[
            inbox.ConfirmedItem(action_id="line.capture." + session.id,
                                target=target, fields=fields)]),
            Response(), user=user, db=db)
        outcome = result["results"][0]["status"]
        session.status = ("confirmed" if outcome in ("CREATED", "ALREADY_APPLIED")
                          else "unknown" if outcome == "UNKNOWN" else "pending")
        await db.commit()
        return _preview(session, cfg, user, identity, make_token, postback_action, quick_reply)
    else:
        return _reply("無效或已失效的操作，請重新輸入內容。", [], quick_reply)
    return _preview(session, cfg, user, identity, make_token, postback_action, quick_reply)
