"""Life LINE v2: scoped postback commands and bounded activity Flex replies.

This module adds no new database, push channel, external crawler, or public API.
Rich Menu v1 still works unchanged until Owner accepts the v2 eight-grid release.
"""
import base64
import binascii
import hashlib
import hmac
import json
import re
from datetime import datetime, timedelta, timezone
from urllib.parse import parse_qsl

from fastapi import HTTPException, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import curated, curated_actions
from app.api.ui_policies import effective_features
from app.models.curated import CuratedActivity
from app.services.line_channel import liff_url

MAX_ACTION_BYTES = 300
CAROUSEL_LIMIT = 6
MAX_CAROUSEL_BYTES = 48_000  # Leave room below LINE's 50 KB JSON limit.
TOKEN_TTL = timedelta(days=7)
SUPPORTED_MENU = frozenset(("events.latest", "events.tags", "events.saved"))
ALLOWED_COMMANDS = frozenset((
    "events.latest", "events.tags", "events.saved", "events.page",
    "events.tag", "events.tags_page", "events.save",
))
# Other eight-grid entries are explicitly deferred to V2-03; the old LIFF
# functionality remains reachable as a safe fallback until implemented.
DEFERRED_MENU = {
    "capture.start": "capture",
    "today.view": "today",
    "search.start": "search",
    "tasks.list": "tasks",
    "shopping.list": "shopping",
    "calendar.today": "calendar",
}


def _binding_scope(cfg: dict, user: dict, identity: str) -> str:
    raw = "|".join((cfg["namespace"], user["sub"], identity))
    return hashlib.sha256(raw.encode()).hexdigest()[:20]


def make_token(cfg: dict, user: dict, identity: str, action: str, **fields) -> str:
    """Short signed, expiring, actor-scoped LINE postback (no bearer/session)."""
    if action not in ALLOWED_COMMANDS:
        raise ValueError("Unknown action")
    if any(k not in {"o", "s", "k", "i", "b", "m"} for k in fields):
        raise ValueError("Unknown token attribute")
    payload = {"a": action, "e": int((datetime.now(timezone.utc) + TOKEN_TTL).timestamp()),
               "u": _binding_scope(cfg, user, identity), **fields}
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode()
    encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    sig = hmac.new(cfg["channel_secret"].encode(), encoded.encode(), hashlib.sha256).digest()[:16]
    token = "v2:" + encoded + "." + base64.urlsafe_b64encode(sig).decode().rstrip("=")
    if len(token.encode()) > MAX_ACTION_BYTES:
        raise ValueError("Postback exceeds LINE 300-byte limit")
    return token


def read_token(token: str, cfg: dict, user: dict, identity: str) -> dict:
    if not token.startswith("v2:") or len(token.encode()) > MAX_ACTION_BYTES:
        raise ValueError("Invalid postback")
    try:
        encoded, signature = token[3:].split(".", 1)
        expected = hmac.new(cfg["channel_secret"].encode(), encoded.encode(), hashlib.sha256).digest()[:16]
        actual = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        if not hmac.compare_digest(expected, actual):
            raise ValueError("Invalid postback signature")
        data = json.loads(base64.urlsafe_b64decode(encoded + "=" * (-len(encoded) % 4)))
    except (ValueError, TypeError, UnicodeDecodeError, binascii.Error) as exc:
        raise ValueError("Invalid postback payload") from exc
    if (not isinstance(data, dict) or data.get("a") not in ALLOWED_COMMANDS
            or data.get("u") != _binding_scope(cfg, user, identity)
            or type(data.get("e")) is not int or data["e"] < int(datetime.now(timezone.utc).timestamp())):
        raise ValueError("Expired or unauthorized postback")
    return data


def _menu_command(data: str) -> str | None:
    """Only accept strict v2 public menu commands, not arbitrary postback data."""
    if len(data) > MAX_ACTION_BYTES:
        return None
    pairs = parse_qsl(data, keep_blank_values=True)
    if len(pairs) != 2 or set(pairs) != {("v", "2"), ("cmd", dict(pairs).get("cmd"))}:
        return None
    cmd = dict(pairs).get("cmd")
    return cmd if cmd in SUPPORTED_MENU or cmd in DEFERRED_MENU else None


def postback_action(label: str, data: str) -> dict:
    if len(label) > 20 or len(data.encode()) > MAX_ACTION_BYTES:
        raise ValueError("Invalid LINE action length")
    return {"type": "postback", "label": label, "data": data}


def quick_reply(actions: list[dict]) -> dict:
    if len(actions) > 13:
        raise ValueError("LINE permits at most 13 quick replies")
    return {"items": [{"type": "action", "action": action} for action in actions]}


def _text_reply(text: str, actions: list[dict] | None = None) -> list[dict]:
    msg = {"type": "text", "text": text[:4900]}
    if actions:
        msg["quickReply"] = quick_reply(actions)
    return [msg]


def _category_key(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()[:20]


async def _activity_access(db: AsyncSession, user: dict) -> None:
    flags = await effective_features(db, user)
    if not any(flag["available"] for flag in flags if flag["key"] in ("explore", "opportunities")):
        raise HTTPException(403, "Activity features unavailable")


async def _categories(db: AsyncSession) -> list[str]:
    # Limit the in-chat selector; the Life App retains the complete filter UI.
    today = datetime.now(curated.TAIPEI).date()
    query = (select(CuratedActivity.category)
             .where(CuratedActivity.category.is_not(None),
                    CuratedActivity.category != "",
                    curated._active_activity_predicate(today, "explore"))
             .distinct().order_by(CuratedActivity.category).limit(200))
    result = (await db.scalars(query)).all()
    return [value for value in result if isinstance(value, str) and value.strip()]


def _group_id(row: dict) -> str:
    group = row.get("parent_event_key") or row.get("handoff_event_key")
    return "handoff:" + group if group else "legacy:" + str(row.get("identity_key", ""))


async def _activity_page(db: AsyncSession, user: dict, *, category: str | None = None,
                         saved_only: bool = False, offset: int = 0, snapshot: int | None = None) -> dict:
    if not isinstance(offset, int) or offset < 0 or offset > 50000:
        raise ValueError("Invalid page offset")
    # Microsecond precision avoids moving page boundaries backwards when an
    # initial request and a new import land in the same second.
    as_of = (datetime.fromtimestamp(snapshot / 1_000_000, tz=timezone.utc)
             if snapshot is not None else datetime.now(timezone.utc))
    # Reuse the EXISTING PostgreSQL group query and permissions, never copy its
    # filter/sort/verification logic into an ad-hoc LINE SQL statement.
    page = await curated.list_curated(
        response=Response(), limit=CAROUSEL_LIMIT, offset=offset,
        city=None, category=category, starts_from=None, min_importance=1,
        _user=user, db=db, entry="explore", keyword=None, quick="latest",
        region=None, district=None, fee_kind=None, saved_only=saved_only,
        verification_status=None, as_of=as_of,
    )
    seen = set()
    items = []
    for row in page["items"]:
        key = _group_id(row)
        if key in seen:
            continue
        seen.add(key)
        items.append(row)
    return {**page, "items": items[:CAROUSEL_LIMIT], "snapshot_us": int(as_of.timestamp() * 1_000_000)}


def _safe_source(url: str | None) -> str | None:
    if not isinstance(url, str):
        return None
    try:
        return curated.normalize_url(url)
    except ValueError:
        return None


def _bubble(row: dict, cfg: dict, user: dict, identity: str) -> dict:
    name = (row.get("title") or "未命名活動")[:95]
    start, end = row.get("starts_on"), row.get("ends_on")
    date_label = str(start) if start else "日期未提供"
    if end and start and end != start:
        date_label += " ～ " + str(end)
    city = (row.get("city") or "地點未提供")[:40]
    tag = (row.get("category") or "未分類")[:34]
    fees = {"free": "免費", "paid": "付費", "conditional_free": "條件免費"}.get(row.get("fee_kind"), "費用未知")
    status = "已核證" if row.get("verification_status") == "verified" else "待核對"
    saved = bool(row.get("saved"))
    item_id = str(row.get("identity_key", ""))
    if not re.fullmatch(r"[0-9a-f]{64}", item_id):
        raise ValueError("Invalid curated activity identity")
    action = postback_action("取消收藏" if saved else "收藏",
                             make_token(cfg, user, identity, "events.save", i=item_id, b=not saved))
    footer = [{"type": "button", "style": "primary", "color": "#23765C", "height": "sm", "action": action}]
    source = _safe_source(row.get("original_url"))
    if source:
        footer.append({"type": "button", "style": "link", "height": "sm",
                       "action": {"type": "uri", "label": "活動來源", "uri": source}})
    return {
        "type": "bubble", "size": "mega",
        "body": {"type": "box", "layout": "vertical", "spacing": "md", "contents": [
            {"type": "text", "text": name, "weight": "bold", "size": "lg", "wrap": True, "maxLines": 2},
            {"type": "text", "text": date_label[:100], "size": "sm", "color": "#4F675D", "wrap": True},
            {"type": "text", "text": (city + " · " + tag)[:90], "size": "sm", "wrap": True},
            {"type": "text", "text": fees + " · " + status, "size": "xs", "color": "#526D62"},
        ]},
        "footer": {"type": "box", "layout": "vertical", "spacing": "sm", "contents": footer},
    }


def _menu_actions(cfg, user, identity, *, tag_key=None, category=None, offset=0,
                  snapshot=None, saved=False, has_more=False) -> list[dict]:
    actions = []
    if has_more:
        fields = {"o": offset + CAROUSEL_LIMIT, "s": snapshot, "m": int(saved)}
        if tag_key:
            fields["k"] = tag_key
        actions.append(postback_action("下一批", make_token(cfg, user, identity, "events.page", **fields)))
    actions.extend([
        postback_action("最新上架", make_token(cfg, user, identity, "events.latest")),
        postback_action("依分類看", make_token(cfg, user, identity, "events.tags")),
        postback_action("已收藏", make_token(cfg, user, identity, "events.saved")),
        {"type": "uri", "label": "Life 更多活動", "uri": cfg["origin"] + "/more/explore"},
    ])
    return actions


def _carousel(rows: list[dict], cfg: dict, user: dict, identity: str,
              *, options: list[dict], title: str) -> list[dict]:
    if not rows:
        return _text_reply("目前沒有符合條件的活動。可換分類或到 Life 查看更多。", options)
    cards = []
    for row in rows[:CAROUSEL_LIMIT]:
        cards.append(_bubble(row, cfg, user, identity))
        content = {"type": "carousel", "contents": cards}
        if len(json.dumps(content, ensure_ascii=False, separators=(",", ":")).encode()) > MAX_CAROUSEL_BYTES:
            cards.pop()
            break
    if not cards:
        return _text_reply("活動摘要過長，請開啟 Life 查看。", options)
    return [{
        "type": "flex", "altText": (title + "（左右滑動查看）")[:400],
        "contents": {"type": "carousel", "contents": cards},
        "quickReply": quick_reply(options),
    }]


async def _show_page(cfg: dict, user: dict, identity: str, db: AsyncSession,
                     *, category: str | None = None, saved: bool = False,
                     offset: int = 0, snapshot: int | None = None) -> list[dict]:
    data = await _activity_page(db, user, category=category, saved_only=saved,
                                offset=offset, snapshot=snapshot)
    actions = _menu_actions(cfg, user, identity, tag_key=_category_key(category) if category else None,
                            offset=offset, snapshot=data["snapshot_us"], saved=saved,
                            has_more=bool(data.get("has_more")))
    title = "Life 已收藏活動" if saved else "Life 最新上架活動"
    if category:
        title += " · " + category[:30]
    return _carousel(data["items"], cfg, user, identity, options=actions, title=title)


async def _show_tags(cfg: dict, user: dict, identity: str, db: AsyncSession,
                     offset: int = 0) -> list[dict]:
    cats = await _categories(db)
    if not isinstance(offset, int) or offset < 0 or offset >= max(len(cats), 1):
        return _text_reply("分類清單已更新，請重新選擇。",
                           [postback_action("重新選分類", make_token(cfg, user, identity, "events.tags"))])
    batch = cats[offset:offset+8]
    choices = [postback_action(cat[:20],
               make_token(cfg, user, identity, "events.tag", k=_category_key(cat))) for cat in batch]
    if offset + len(batch) < len(cats):
        choices.append(postback_action("更多分類", make_token(cfg, user, identity, "events.tags_page",
                                                             o=offset+len(batch))))
    choices.append(postback_action("最新活動", make_token(cfg, user, identity, "events.latest")))
    choices.append({"type": "uri", "label": "Life 進階篩選", "uri": cfg["origin"] + "/more/explore"})
    return _text_reply("請選活動分類；此選單取自 Life 已上架資料，不代表完整多標籤系統。"
                       if cats else "目前沒有可用的活動分類。", choices)


async def handle_postback(event: dict, identity: str, cfg: dict,
                          user: dict, db: AsyncSession) -> list[dict]:
    data = (event.get("postback") or {}).get("data")
    if not isinstance(data, str) or len(data.encode()) > MAX_ACTION_BYTES:
        return _text_reply("選單指令無效。請重新開啟選單。")
    public = _menu_command(data)
    if public in DEFERRED_MENU:
        return _text_reply("這項功能的 LINE 卡片正在分階段開發，可先使用原 Life 頁面。",
                           [{"type": "uri", "label": "開啟 Life", "uri": liff_url(cfg, page=DEFERRED_MENU[public])}])
    if public is None:
        try:
            command = read_token(data, cfg, user, identity)
        except ValueError:
            return _text_reply("此按鈕已失效或與目前帳號不符，請從選單重新開始。")
    else:
        command = {"a": public}
    if command["a"] not in ALLOWED_COMMANDS:
        return _text_reply("尚未支援這項操作。")
    await _activity_access(db, user)
    cmd = command["a"]
    if cmd == "events.latest":
        return await _show_page(cfg, user, identity, db)
    if cmd == "events.saved":
        return await _show_page(cfg, user, identity, db, saved=True)
    if cmd == "events.tags":
        return await _show_tags(cfg, user, identity, db)
    if cmd == "events.tags_page":
        return await _show_tags(cfg, user, identity, db, offset=command.get("o", 0))
    if cmd == "events.tag" or cmd == "events.page":
        tag_hash = command.get("k")
        category = None
        if tag_hash is not None:
            cats = await _categories(db)
            category = next((x for x in cats if _category_key(x) == tag_hash), None)
            if category is None:
                return _text_reply("分類已調整，請重新選擇。",
                                   [postback_action("選分類", make_token(cfg, user, identity, "events.tags"))])
        if cmd == "events.tag":
            return await _show_page(cfg, user, identity, db, category=category)
        return await _show_page(cfg, user, identity, db, category=category,
                                offset=command.get("o", 0), snapshot=command.get("s"),
                                saved=bool(command.get("m", 0)))
    if cmd == "events.save":
        activity_id, active = command.get("i"), command.get("b")
        if not isinstance(activity_id, str) or not re.fullmatch(r"[0-9a-f]{64}", activity_id) or type(active) is not bool:
            return _text_reply("收藏指令無效，請重新查看活動。")
        today = datetime.now(curated.TAIPEI).date()
        permitted = (await db.scalars(
            select(CuratedActivity.identity_key).where(
                CuratedActivity.identity_key == activity_id,
                curated._active_activity_predicate(today, "explore"))
        )).first()
        if permitted is None:
            return _text_reply("活動已更新或結束，請重新開啟活動清單。")
        # Reuse existing owner-scoped CuratedPersonalAction service. Explicit
        # target state (not toggle) means postback redelivery cannot invert it.
        await curated_actions.set_action(activity_id, "save",
                                         curated_actions.ActionWrite(active=active),
                                         user=user, db=db)
        return _text_reply("已收藏，可在 Life 查看。" if active else "已取消收藏。",
                           [postback_action("最新活動", make_token(cfg, user, identity, "events.latest")),
                            postback_action("已收藏", make_token(cfg, user, identity, "events.saved"))])
    return _text_reply("選單指令未支援。")
