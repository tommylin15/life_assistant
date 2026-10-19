"""Gmail V2: local-only semantic fallback and conservative date evidence.

No outbound AI calls. No runtime model download. Embeddings are OPTIONAL:
an approved multilingual SentenceTransformer checkpoint must already exist on
local disk and GMAIL_RADAR_LOCAL_MODEL_PATH must point to it.
"""
from __future__ import annotations

import math
import os
import re
from dataclasses import dataclass
from datetime import date
from functools import lru_cache
from pathlib import Path

CLASSIFIER_VERSION = "local-v2.1"

# Short, de-identified reference intents. Do not train on Gmail data.
EXAMPLES: dict[str, tuple[str, ...]] = {
    "billing": (
        "您的信用卡繳費期限即將到期，請確認是否已繳款",
        "電信費帳單已出帳，請在截止日前付款",
        "Payment reminder: your bill is due soon",
    ),
    "pickup": ("包裹已到門市，請於期限前取貨", "Your package is ready for pickup"),
    "booking": ("預約確認通知，請核對訂位時間", "Your appointment has been confirmed"),
    "travel": ("航班時間異動，請確認最新出發時間", "Flight change requires attention"),
    "deadline": ("文件需要補件，請於期限內辦理", "Response deadline is approaching"),
    "security": ("警告：偵測到未授權的帳戶登入", "Suspicious account activity detected"),
    "account": ("付款失敗導致帳號即將停用", "Subscription payment problem requires action"),
    "refund": ("退款申請遭拒，需要您處理", "Your refund request requires action"),
    "administrative": ("學校通知需要家長回覆及繳交同意書", "Government document requires response"),
    "authorization": ("新的第三方程式取得帳戶存取權，請確認授權", "App permissions have changed"),
}

# Never elevate a routine/no-action email or overt advertising via similarity.
NO_ACTION = re.compile(
    r"(?i)(暫無需繳款|本期無需繳款|不需繳款|無需繳款|"
    r"已完成繳費|付款成功|已繳清|無須處理|不需要採取任何行動|"
    r"優惠|促銷|電子報|廣告|特價|折扣|newsletter|unsubscribe|"
    r"payment received|payment successful|no action (?:is )?required)"
)
# Specific evidence only. Month/day alone is retained as text: never invent a year.
DUE = re.compile(
    r"(?:繳款截止|繳費截止|付款期限|繳費期限|繳款期限|到期日|截止日|"
    r"payment due|due date|deadline)"
    r"[\s:：為至於]*"
    r"(?P<stamp>(?:民國)?\d{2,4}[\-/年]\d{1,2}[\-/月]\d{1,2}日?|"
    r"\d{1,2}月\d{1,2}日)",
    re.IGNORECASE,
)
BARE_DUE = re.compile(
    r"(?:繳款截止|繳費截止|繳款期限|到期日|截止日).{0,12}?"
    r"(?P<stamp>\d{1,2}月\d{1,2}日)"
)


@dataclass(frozen=True)
class LocalDecision:
    category: str | None
    source: str
    reason_code: str
    due_date: date | None = None
    due_text: str | None = None


def extract_due(subject: str, snippet: str) -> tuple[date | None, str | None]:
    text = (subject + " " + snippet)[:1000]
    found = DUE.search(text) or BARE_DUE.search(text)
    if not found:
        return None, None
    raw = found.group("stamp").strip()
    # Month/day without an explicit year is not a complete ISO date.
    if not re.search(r"\d{2,4}[\-/年]", raw):
        return None, raw[:32]
    cleaned = raw.replace("民國", "").replace("年", "/").replace("月", "/").replace("日", "")
    bits = re.split(r"[-/]", cleaned)
    if len(bits) != 3:
        return None, raw[:32]
    try:
        year, month, day = map(int, bits)
        if year < 1911:
            # ROC years must be explicit; a two-digit Gregorian year is not inferred.
            if not (raw.startswith("民國") or "年" in raw or len(bits[0]) == 3):
                return None, raw[:32]
            year += 1911
        return date(year, month, day), raw[:32]
    except ValueError:
        return None, raw[:32]


@lru_cache(maxsize=2)
def _load_local_model(path: str):
    if not path or not Path(path).is_dir():
        raise RuntimeError("local_model_artifact_missing")
    # Explicit offline mode; no remote model resolution and no dynamic code.
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(path, device="cpu", trust_remote_code=False, local_files_only=True)


@lru_cache(maxsize=2)
def _examples_embeddings(path: str):
    model = _load_local_model(path)
    phrases = [(category, phrase) for category, examples in EXAMPLES.items() for phrase in examples]
    vectors = model.encode([phrase for _, phrase in phrases], normalize_embeddings=True)
    return model, phrases, vectors


def _semantic_category(subject: str, snippet: str, *, path: str) -> str | None:
    # Only local checkpoint files; missing dependencies/artifact mean no semantics,
    # not an excuse to call an external model.
    if not path or not Path(path).is_dir():
        return None
    try:
        model, phrases, vectors = _examples_embeddings(path)
        query_vector = model.encode([(" " .join((subject, snippet)))[:800]],
                                    normalize_embeddings=True)[0]
        scores: dict[str, float] = {}
        for (category, _), vector in zip(phrases, vectors):
            similarity = sum(float(a) * float(b) for a, b in zip(query_vector, vector))
            if math.isfinite(similarity):
                scores[category] = max(scores.get(category, -1.0), similarity)
        ranked = sorted(scores.items(), key=lambda pair: pair[1], reverse=True)
        # Conservative starting guard, NOT a calibrated probability.
        if ranked and ranked[0][1] >= 0.80 and (
            len(ranked) == 1 or ranked[0][1] - ranked[1][1] >= 0.08
        ):
            return ranked[0][0]
    except (ImportError, OSError, RuntimeError, ValueError, TypeError):
        return None
    return None


def classify_local(subject: str, snippet: str, rule_category: str | None,
                   *, model_path: str | None = None) -> LocalDecision:
    stamp, text = extract_due(subject, snippet)
    if rule_category:
        # Rule classifier already implements exact advertising exclusions.
        return LocalDecision(rule_category, "rules", "explicit_action", stamp, text)
    candidate = (" ".join((subject, snippet)))[:1000]
    if not subject.strip() or NO_ACTION.search(candidate):
        return LocalDecision(None, "rules", "not_actionable")
    model_path = os.environ.get("GMAIL_RADAR_LOCAL_MODEL_PATH", "") if model_path is None else model_path
    category = _semantic_category(subject, snippet, path=model_path)
    if category:
        return LocalDecision(category, "local_semantic", "semantic_review", stamp, text)
    return LocalDecision(None, "rules", "no_confident_match")
