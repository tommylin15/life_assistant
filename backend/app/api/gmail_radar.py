"""Manual-only Gmail action radar; never schedules or fetches entire mailboxes."""
import asyncio
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
from app.services.gmail_local_classifier import CLASSIFIER_VERSION, classify_local

router = APIRouter(prefix="/integrations/google/gmail/radar", tags=["gmail-radar"])

QUICK_LIMIT = 20
BACKFILL_BATCH = 40
THREE_DAY_PAGE_SIZE = 500
THREE_DAY_MAX_PAGES = 4
THREE_DAY_QUERY = "newer_than:3d -in:spam -in:trash"
SEVEN_DAY_QUERY = "newer_than:7d -in:spam -in:trash"
QUICK_QUERY = "newer_than:7d -in:spam -in:trash"


# Conservative, deterministic metadata-only classification. Categories are
# user actions to REVIEW, never a judgment that the sender or the alert is real.
#
# Priority: promotional subject suppression -> security -> refund/order ->
# account/fees -> administrative follow-ups -> original five classes.
# Do not classify generic OTPs, order confirmations, newsletters or happy-path
# refund status as risk requiring a new Life task.
_PROMOTION = re.compile(
    r"(?i)(unsubscribe|取消訂閱|電子報|廣告\s*EDM|促銷|優惠券|優惠碼|折扣碼|"
    r"優惠|特惠|限時折扣|特賣|特價|買一送一|好康|"
    r"black friday|newsletter|promo code|coupon code|special offer|"
    r"flash sale|limited.time offer|discount code|save \d+%|"
    r"upgrade offer)"
)

# Titles are strong evidence; snippets require narrower, explicit exception
# phrases because ordinary emails contain legal footers and ad copy.
_SECURITY_TITLE = (
    "異常登入", "可疑登入", "非本人登入", "不明裝置登入", "陌生裝置登入",
    "新裝置登入警告", "帳戶遭入侵", "帳號遭入侵", "帳戶被盜", "帳號被盜",
    "帳戶遭鎖定", "帳號遭鎖定", "密碼遭變更", "密碼已變更",
    "密碼重設要求", "非本人操作", "疑似盜刷", "可疑交易", "異常交易",
    "非本人交易", "未授權交易", "安全性警告", "安全警報",
    "雙重驗證已停用", "兩步驟驗證已停用", "復原信箱已變更",
    "unusual sign-in", "suspicious sign-in", "unrecognized sign-in",
    "unknown device sign-in", "new device sign-in", "account compromised",
    "account locked", "account breached", "password changed",
    "password reset requested", "security alert", "fraud alert",
    "suspicious transaction", "unauthorized transaction",
    "unauthorized access", "two-factor authentication disabled",
)
_SECURITY_SNIPPET = (
    "偵測到異常登入", "發現可疑登入", "發現未授權交易", "非本人登入",
    "偵測到可疑活動", "您的帳號可能遭入侵", "疑似盜刷",
    "unusual sign-in detected", "suspicious sign-in detected",
    "unauthorized access detected", "unauthorized transaction detected",
    "fraudulent charge detected",
)
_ACCOUNT_TITLE = (
    "付款失敗", "扣款失敗", "自動扣款失敗", "付款方式失效",
    "請更新付款方式", "訂閱即將續費", "即將自動續訂", "訂閱到期提醒",
    "會員資格即將到期", "帳戶即將停用", "帳號即將停用",
    "帳戶已停用", "帳號已停用", "服務即將停用", "服務將被暫停",
    "訂閱費用調整", "訂閱價格調整", "續訂費用", "扣款通知",
    "儲存空間即將用盡", "帳戶儲存空間不足",
    "payment failed", "payment declined", "payment method declined",
    "update your payment method", "subscription renewal notice",
    "upcoming subscription renewal", "subscription expires",
    "account suspension", "account suspended", "service suspension",
    "storage almost full", "subscription price increase",
    "billing issue", "renewal charge",
    # Non-billing product data can be lost when a paused project is frozen.
    # Require explicit project/service freeze wording; a plain "paused" in
    # account activity or a routine product newsletter is not enough.
    "project is being permanently frozen", "project will be permanently frozen",
    "project permanently frozen", "project about to be frozen",
    "your project has been paused", "your project is paused",
    "專案即將永久凍結", "專案將被永久凍結", "專案即將凍結", "專案已暫停",
)
_ACCOUNT_SNIPPET = (
    "您的付款失敗", "扣款失敗", "付款方式已失效",
    "帳戶即將停用", "訂閱將自動續費", "續訂費用",
    "your payment failed", "your payment was declined",
    "update your payment method", "your account will be suspended",
    "your subscription will renew",
)
_REFUND_TITLE = (
    "退款失敗", "退費失敗", "退款遭拒", "退款申請遭拒", "退費遭拒", "退款延遲",
    "退款尚未入帳", "退款申請待補件", "退款需要補件",
    "退款期限", "退款申請截止", "退貨逾期", "退貨申請待處理",
    "訂單取消", "訂單異常", "訂單未成立", "訂單付款失敗",
    "訂單需要處理", "賣家取消訂單", "商品未收到", "爭議款",
    "refund failed", "refund was denied", "refund has been denied",
    "refund denied", "refund was rejected", "refund rejected",
    "refund was delayed", "refund delayed", "refund not received",
    "refund requires action",
    "return request requires action", "order cancelled", "order canceled",
    "order failed", "order payment failed", "order issue",
    "order requires action",
)
_REFUND_SNIPPET = (
    "退款申請遭拒", "退款失敗", "退款需要補件", "訂單已取消",
    "訂單付款失敗", "賣家已取消訂單",
    "your refund was denied", "your refund failed",
    "your order was canceled", "your order was cancelled",
    "payment for your order failed",
)
_ADMIN_TITLE = (
    "公文請回覆", "公文待回覆", "政府補件", "政府案件待補件",
    "戶政補件", "稅務補件", "申請案請補件", "學校請回覆",
    "學校補件", "學籍資料補件", "同意書繳交期限",
    "家長同意書待繳", "選課截止", "報到期限",
    "公司待簽核", "工作待回覆", "主管請回覆",
    "請於期限內回覆", "審核待補件", "文件繳交期限",
    "government action required", "government document required",
    "official response required", "school action required",
    "school consent form due", "approval requires your action",
    "response deadline", "document submission deadline",
)
_ADMIN_SNIPPET = (
    "請於期限內回覆", "請於期限內補件", "請在截止日前繳交",
    "需您簽核", "請家長回覆", "請繳交同意書",
    "government action required", "school action required",
    "please submit the required documents",
    "your response is required by",
)
# Third-party authorization is a *review item*, not a confirmed attack.
# Require explicit new app access or permission-change phrasing, not a generic
# one-time password, successful Google sign-in, or ordinary OAuth confirmation.
_ACCESS_REVIEW = re.compile(
    r"(?i)(第三方.{0,18}(?:應用|程式|app).{0,24}(?:權限|存取|授權)|"
    r"(?:應用程式|第三方程式|第三方應用).{0,26}(?:已取得|獲得|已授予|已變更).{0,20}(?:存取權|權限)|"
    r"(?:已授予|已允許).{0,36}(?:應用程式|第三方).{0,20}(?:存取|授權)|"
    r"(?:授權範圍|應用程式權限|帳戶存取權).{0,14}(?:變更|擴大|新增)|"
    r"new app (?:has|was granted) access|"
    r"(?:an? )?app has access to your (?:google|microsoft|apple) account|"
    r"granted access to your (?:google|microsoft|apple) account|"
    r"third.party (?:app )?access (?:granted|changed)|"
    r"(?:app|application) permissions? (?:granted|changed|expanded))"
)

_ACCESS_SNIPPET = re.compile(
    r"(?i)(第三方應用程式.{0,26}(?:已取得|取得了|獲得|存取權限|存取權)|"
    r"(?:新|其他)應用程式.{0,26}(?:存取您的|存取你的|取得).{0,15}(?:帳號|帳戶|資料)|"
    r"new app has access to your (?:google|microsoft|apple) account|"
    r"you granted.{0,55}access to your (?:google|microsoft|apple) account)"
)

_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("billing", ("繳費期限", "繳費通知", "繳款通知", "繳款期限", "繳款截止",
                 "繳款提醒", "付款期限", "付款提醒", "帳單到期", "帳單通知",
                 "電子帳單", "e帳單", "信用卡帳單",
                 "payment due", "bill due", "statement due")),
    ("pickup", ("取貨通知", "取貨期限", "包裹已到", "貨到門市", "package ready", "ready for pickup")),
    ("booking", ("訂房確認", "訂位確認", "預約確認", "預約成功", "booking confirmation",
                 "reservation confirmed", "appointment confirmed")),
    ("travel", ("航班異動", "航班取消", "機票訂位", "航班確認", "flight canceled",
                "flight cancelled", "flight change")),
    ("deadline", ("報名截止", "補件通知", "請於期限內", "申請期限", "registration deadline",
                  "action required", "response required")),
)


def _matches(text_value: str, phrases: tuple[str, ...]) -> bool:
    return any(phrase in text_value for phrase in phrases)


def classify_message(subject: str, snippet: str) -> str | None:
    """Classify a high-confidence actionable EMAIL, not a verified security fact.

    Restricts to metadata (subject and bounded snippet). Deliberately
    undershoots recall when a benign ad and important message are ambiguous.
    """
    title = " ".join(subject.casefold().split())
    preview = " ".join(snippet.casefold().split())[:500]
    if not title or _PROMOTION.search(title):
        return None

    additional = (
        ("security", _SECURITY_TITLE, _SECURITY_SNIPPET),
        ("refund", _REFUND_TITLE, _REFUND_SNIPPET),
        ("account", _ACCOUNT_TITLE, _ACCOUNT_SNIPPET),
        ("administrative", _ADMIN_TITLE, _ADMIN_SNIPPET),
    )
    # Subject intent takes priority over a footnote, quoted message, or
    # secondary event mentioned in Gmail's weaker preview snippet.
    for category, title_phrases, _ in additional:
        if _matches(title, title_phrases):
            return category
    if _ACCESS_REVIEW.search(title):
        return "authorization"
    for category, phrases in _RULES:
        if _matches(title, phrases):
            # Routine e-bills with an explicit "no payment required" notice
            # are not actionable; do not turn them into payment reminders.
            if category == "billing" and _matches(title, ("電子帳單", "e帳單", "帳單通知", "信用卡帳單")):
                if _matches(preview, ("暫無需繳款", "本期無需繳款", "不需繳款", "無需繳款")):
                    return None
            return category

    # A generic title with promotional snippet must not be escalated just
    # because the advertisement describes a hypothetical risk or fee.
    if _PROMOTION.search(preview):
        return None
    for category, _, snippet_phrases in additional:
        if _matches(preview, snippet_phrases):
            return category
    if _ACCESS_SNIPPET.search(preview):
        return "authorization"
    for category, phrases in _RULES:
        # Snippets are weaker evidence: match explicit payment/deadline wording
        # rather than a generic mention of a bill or a promotional offer.
        snippet_phrases = phrases[:3]
        if category == "billing":
            snippet_phrases += ("繳款截止", "繳費截止", "本期帳單應繳", "應繳總額",
                                "payment is due", "payment deadline")
        if _matches(preview, snippet_phrases):
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
        "classification_source": item.classification_source,
        "classifier_version": item.classifier_version,
        "reason_code": item.reason_code,
        "due_date": item.due_date,
        "due_text": item.due_text,
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
                "three_day_complete": False,
                "seven_day_count": None, "seven_day_remaining": None,
                "seven_day_complete": False,
                "classifier_version": CLASSIFIER_VERSION}
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
        "seven_day_count": state.seven_day_count,
        "seven_day_remaining": state.seven_day_remaining,
        "seven_day_complete": state.seven_day_complete,
        "classifier_version": CLASSIFIER_VERSION,
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


async def _list_recent_ids(db: AsyncSession, sub: str, scope: str, query: str):
    """Count actual enumerated message IDs, not Gmail resultSizeEstimate."""
    found: list[str] = []
    unique: set[str] = set()
    page_token: str | None = None
    complete = False
    for _ in range(THREE_DAY_MAX_PAGES):
        params: dict[str, str | int] = {
            "q": query, "maxResults": THREE_DAY_PAGE_SIZE,
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


async def _list_three_day_ids(db: AsyncSession, sub: str, scope: str):
    return await _list_recent_ids(db, sub, scope, THREE_DAY_QUERY)


async def _run_scan(user: dict, db: AsyncSession, *, kind: Literal["quick", "backfill", "recheck", "seven_day"]):
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
    seven_day_ids: list[str] = []
    seven_day_listed_all = False
    if kind == "seven_day":
        seven_day_ids, seven_day_listed_all = await _list_recent_ids(
            db, sub, scope, SEVEN_DAY_QUERY)

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

    lookup_ids = list(dict.fromkeys([*three_day_ids, *seven_day_ids, *selected]))
    seen_rows: dict[str, GmailRadarSeen | None] = {}
    if lookup_ids:
        result = await db.execute(select(GmailRadarSeen).where(
            GmailRadarSeen.user_sub == sub,
            GmailRadarSeen.gmail_message_id.in_(lookup_ids),
        ))
        for row in result.scalars().all():
            # Lightweight mocks in older tests return bare ID strings.
            if isinstance(row, GmailRadarSeen):
                seen_rows[row.gmail_message_id] = row
            else:
                seen_rows[str(row)] = None
    seen_ids = set(seen_rows)
    # Legacy records are eligible for re-evaluation under upgraded rules.
    stale_ids = {message_id for message_id, row in seen_rows.items()
                 if row is not None and row.classifier_version != CLASSIFIER_VERSION}

    if kind == "backfill":
        # Progress over unprocessed or old-classifier IDs.
        selected = [message_id for message_id in three_day_ids
                    if message_id not in seen_ids or message_id in stale_ids][:BACKFILL_BATCH]
    elif kind == "seven_day":
        selected = [message_id for message_id in seven_day_ids
                    if message_id not in seen_ids or message_id in stale_ids][:BACKFILL_BATCH]
    elif kind == "recheck":
        # Explicit and bounded: revisit up to 40 recent IDs, including ones
        # excluded by old classifier rules, WITHOUT deleting existing receipts.
        selected = three_day_ids[:BACKFILL_BATCH]
    checked, added, skipped, failed = 0, 0, 0, 0
    newly_seen: set[str] = set()
    refreshed: set[str] = set()
    for message_id in selected:
        checked += 1
        if (kind != "recheck" and message_id in seen_ids and message_id not in stale_ids) or message_id in newly_seen:
            skipped += 1
            continue
        existing = await db.scalar(select(GmailRadarItem.id).where(
            GmailRadarItem.user_sub == sub,
            GmailRadarItem.gmail_message_id == message_id,
        ))
        if existing:
            skipped += 1
            if message_id not in seen_ids:
                db.add(GmailRadarSeen(user_sub=sub, gmail_message_id=message_id,
                                     checked_at=now, classifier_version=CLASSIFIER_VERSION))
                newly_seen.add(message_id)
            elif message_id in stale_ids and seen_rows[message_id] is not None:
                seen_rows[message_id].classifier_version = CLASSIFIER_VERSION
                seen_rows[message_id].checked_at = now
                refreshed.add(message_id)
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
            decision = await asyncio.to_thread(
                classify_local, subject, snippet, classify_message(subject, snippet))
            category = decision.category
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
                    classifier_version=CLASSIFIER_VERSION,
                    classification_source=decision.source,
                    reason_code=decision.reason_code,
                    due_date=decision.due_date, due_text=decision.due_text,
                ))
                added += 1
            else:
                skipped += 1
            if message_id not in seen_ids:
                db.add(GmailRadarSeen(user_sub=sub, gmail_message_id=message_id,
                                     checked_at=now, classifier_version=CLASSIFIER_VERSION))
                newly_seen.add(message_id)
            elif message_id in stale_ids and seen_rows[message_id] is not None:
                seen_rows[message_id].classifier_version = CLASSIFIER_VERSION
                seen_rows[message_id].checked_at = now
                refreshed.add(message_id)
        except HTTPException as exc:
            if exc.status_code in (401, 403, 409):
                raise
            failed += 1
        except (ValueError, TypeError, KeyError):
            failed += 1

    covered_ids = (seen_ids - stale_ids) | newly_seen | refreshed
    remaining = sum(message_id not in covered_ids for message_id in three_day_ids)
    seven_remaining = sum(message_id not in covered_ids for message_id in seven_day_ids)
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
    if kind == "seven_day":
        state.seven_day_count = len(seven_day_ids)
        state.seven_day_remaining = seven_remaining
        state.seven_day_complete = seven_day_listed_all and seven_remaining == 0
    await db.commit()
    return {
        "source": "local_v2", "scan_window_days": 7 if kind in ("quick", "seven_day") else 3,
        "limit": QUICK_LIMIT if kind == "quick" else BACKFILL_BATCH,
        "three_day_count_capped": not listed_all,
        "seven_day_count_capped": kind == "seven_day" and not seven_day_listed_all,
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


@router.post("/backfill-seven-days")
async def manual_seven_day_backfill(
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Explicit 40-message batch from seven-day inventory, no scheduling."""
    return await _run_scan(user, db, kind="seven_day")


@router.post("/recheck-three-days")
async def manual_three_day_recheck(
    user: dict = Depends(current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-evaluate 40 most recent three-day messages on explicit request only.

    Does not delete prior seen IDs or change completed/ignored Life receipts.
    """
    return await _run_scan(user, db, kind="recheck")
