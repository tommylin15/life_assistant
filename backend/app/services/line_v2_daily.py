"""LINE-V2-03: authenticated, bounded daily conversation cards.

Uses existing Life owner-scoped domain functions. No new storage, LLM-side
writes, generic SQL executor, secret/token exposure, or implicit calendar
authorization. LIFF is the deliberate full-edit/commit UI.
"""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.ui_policies import feature_gate
from app.services.line_channel import liff_url

TAIPEI = ZoneInfo("Asia/Taipei")
LIMIT = 5


LIFE_PATHS = {"capture": "/capture", "today": "/today", "search": "/more/notes",
              "notes": "/more/notes", "tasks": "/tasks", "shopping": "/more/shopping",
              "calendar": "/calendar", "activities": "/more/explore"}


def _link(cfg, page, label="在 Life 編輯"):
    """Current environment's real Flutter route, never LIFF intermediary."""
    return {"type": "uri", "label": label, "uri": cfg["origin"] + LIFE_PATHS[page]}


def _card(title, detail, action=None):
    content = [
        {"type": "text", "text": str(title)[:95], "weight": "bold",
         "size": "md", "wrap": True, "maxLines": 2},
        {"type": "text", "text": str(detail or "未提供補充資訊")[:220],
         "size": "sm", "color": "#526D62", "wrap": True, "maxLines": 4},
    ]
    bubble = {"type": "bubble", "size": "mega",
              "body": {"type": "box", "layout": "vertical",
                       "spacing": "md", "contents": content}}
    if action:
        bubble["footer"] = {"type": "box", "layout": "vertical", "contents": [
            {"type": "button", "style": "primary", "height": "sm",
             "color": "#23765C", "action": action}
        ]}
    return bubble


def _cards(rows, title, controls, quick_reply, empty="目前沒有資料。"):
    if not rows:
        return [{"type": "text", "text": empty,
                 "quickReply": quick_reply(controls)}]
    return [{"type": "flex", "altText": title[:400],
             "contents": {"type": "carousel", "contents": rows[:LIMIT]},
             "quickReply": quick_reply(controls)}]


def _ts_label(value):
    if not value:
        return "未設定時間"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if dt.tzinfo:
            return dt.astimezone(TAIPEI).strftime("%m/%d %H:%M")
    except (ValueError, TypeError):
        pass
    return "時間未確認"


async def _calendar_for(user, db, days):
    """Read Google Calendar through the existing owner-scoped adapter."""
    from app.api import google_integrations
    await feature_gate("calendar")(user=user, db=db)
    today = datetime.now(TAIPEI).date()
    start = datetime.combine(today, datetime.min.time(), tzinfo=TAIPEI)
    stop = start + timedelta(days=days)
    return (await google_integrations.list_calendar_events(
        time_min=start, time_max=stop, limit=LIMIT,
        user=user, db=db))["events"]


async def handle_daily(cmd, command, identity, cfg, user, db: AsyncSession,
                       make_token, postback_action, text_reply, quick_reply):
    # Import lazily to avoid a circular dependency with the webhook router.
    from app.api import line as line_api

    def token(action, **fields):
        return make_token(cfg, user, identity, action, **fields)

    if cmd == "capture.start":
        await feature_gate("life_inbox")(user=user, db=db)
        return text_reply(
            "請直接輸入內容，例如「牛奶」或「明天下午三點看牙醫」。"
            "我會在 LINE 裡提供購物／待辦／行程／筆記的分類和欄位，"
            "最後由你點選確認才會真正寫入 Life。",
            [_link(cfg, "capture", "Life 進階新增")])

    if cmd == "search.start":
        return text_reply("選擇要查詢的資料類型；也可輸入「查 筆記 關鍵字」、"
                          "「查 待辦 關鍵字」或「查 購物 關鍵字」。", [
            postback_action("筆記", token("search.kind", k="notes")),
            postback_action("待辦", token("search.kind", k="tasks")),
            postback_action("購物", token("search.kind", k="shopping")),
            _link(cfg, "notes", "在 Life 搜尋")])

    if cmd in ("search.kind", "tasks.list", "shopping.list"):
        kind = (command.get("k") if cmd == "search.kind" else
                "tasks" if cmd == "tasks.list" else "shopping")
        if kind not in ("notes", "tasks", "shopping"):
            return text_reply("資料類型無效，請重新開啟搜尋。")
        result = await line_api.lookup(kind, "", user, db)
        rows = []
        for item in result["items"][:LIMIT]:
            action = None
            if kind == "tasks":
                action = postback_action(
                    "標記完成", token("tasks.complete", i=item["id"]))
            elif kind == "shopping":
                action = postback_action(
                    "已購買", token("shopping.set", i=item["id"], b=True))
            details = (item.get("detail") or "")[:110]
            if item.get("date"):
                details += " · " + _ts_label(item["date"])
            rows.append(_card(item["title"], details, action))
        pages = {"notes": "notes", "tasks": "tasks", "shopping": "shopping"}
        labels = {"notes": "筆記", "tasks": "待辦", "shopping": "購物"}
        return _cards(rows, "我的" + labels[kind], [
            _link(cfg, pages[kind], "查看／新增更多"),
            postback_action("重新查詢", token("search.kind", k=kind))
        ], quick_reply, empty="目前沒有符合條件的" + labels[kind] + "。")

    if cmd == "tasks.complete":
        from app.api import tasks as task_api
        await feature_gate("tasks")(user=user, db=db)
        task_id = command.get("i")
        if not isinstance(task_id, str) or len(task_id) > 36:
            return text_reply("待辦按鈕無效，請重新查看清單。")
        await task_api.complete_task(task_id, user=user, db=db)
        return text_reply("待辦已完成；重複操作不會重新新增事項。", [
            postback_action("重新查看待辦", token("tasks.list")),
            _link(cfg, "tasks")])

    if cmd == "shopping.set":
        from app.api import shopping as shopping_api
        from app.models.schemas import ShoppingItemUpdate
        await feature_gate("shopping")(user=user, db=db)
        item_id, done = command.get("i"), command.get("b")
        if not isinstance(item_id, str) or len(item_id) > 36 or done is not True:
            return text_reply("購物按鈕無效，請重新查看清單。")
        # Existing API handles list ownership and execution receipts.
        await shopping_api.update_shopping_item(
            item_id, ShoppingItemUpdate(is_done=True), user=user, db=db)
        return text_reply("已標記購買完成。", [
            postback_action("重新查看購物", token("shopping.list")),
            _link(cfg, "shopping")])

    if cmd in ("today.view", "calendar.today"):
        controls = [_link(cfg, "today" if cmd == "today.view" else "calendar",
                          "查看完整" + ("今日總覽" if cmd == "today.view" else "日曆"))]
        if cmd == "today.view":
            tasks = await line_api.lookup("tasks", "", user, db)
            today = datetime.now(TAIPEI).date()
            due = []
            for item in tasks["items"]:
                try:
                    raw = item.get("date")
                    due_at = datetime.fromisoformat(str(raw)) if raw else None
                    if due_at and due_at.astimezone(TAIPEI).date() <= today:
                        due.append(item)
                except (ValueError, TypeError):
                    continue
            if tasks.get("has_more"):
                task_text = "到期待辦（前 20 筆中）"
            else:
                task_text = "到期待辦"
            tasks_card = _card(task_text, "、".join(x["title"][:30] for x in due[:5]) or
                               "目前查到的待辦沒有今天到期項目")
        else:
            tasks_card = None
        try:
            events = await _calendar_for(user, db, 1 if cmd == "today.view" else 7)
            calendar_cards = [_card(x.get("summary") or "未命名行程",
                                    (x.get("start") or {}).get("date") or
                                    _ts_label((x.get("start") or {}).get("dateTime")))
                              for x in events[:LIMIT]]
            if not calendar_cards:
                calendar_cards = [_card("行程", "所選期間沒有行程")]
        except HTTPException:
            calendar_cards = [_card("日曆授權／權限待處理",
                                    "未能讀取 Google 日曆，請在 Life 重新授權；這不代表沒有行程。")]
        except Exception:
            calendar_cards = [_card("Google 日曆暫時無法查詢",
                                    "查詢結果未知，請回 Life 查核，不能視為沒有行程。")]
        rows = ([tasks_card] if tasks_card else []) + calendar_cards
        return _cards(rows, "Life 今日總覽" if tasks_card else "Life 近期日曆",
                      controls, quick_reply)

    return text_reply("這項操作尚無法確認，請重新開啟選單。")
