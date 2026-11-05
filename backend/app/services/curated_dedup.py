"""
Taiwan Curated Activities Two-Tier Deduplication and Entity Normalization Service.

Resolves real-world multi-source event duplicates (e.g. government announcements,
tourism agency updates, Accupass tickets, BeClass signups) to ensure one canonical
parent_event_key per physical event, complying with 04-upsert.md.
"""
import re
from datetime import date, datetime
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple


def normalize_title(title: str) -> str:
    """Normalize activity title by stripping year prefixes, edition numbers,
    bracketed subtitles, and trailing descriptive clauses.
    
    Examples:
        '2026–2027屏東四重溪溫泉季（四重溪溫泉公園浪漫光影燈海...）' -> '屏東四重溪溫泉季'
        '2026臺灣國際衝浪公開賽（東河金樽漁港沙灘衝浪賽事...）' -> '臺灣國際衝浪公開賽'
        '2026金門老兵召集令「榮耀歸隊・番號集結」' -> '金門老兵召集令'
        '2026士林官邸菊展《菊映方圓》（15大菊花主題展區...）' -> '士林官邸菊展'
    """
    if not title:
        return ""
    t = title.strip()
    # 1. Strip leading edition or prefix e.g. 第34屆, 第十一屆, 【免費報名】
    t = re.sub(r"^[【\[][^】\]]+[】\]]\s*", "", t)
    t = re.sub(r"^第[一二三四五六七八九十百0-9]+屆\s*", "", t)
    # 2. Strip leading CE/ROC years e.g. 2026, 2026-2027, 2026–2027, 115年
    t = re.sub(r"^(202\d|11\d年?)[-–—~]?(202\d|11\d年?)?\s*", "", t)
    t = re.sub(r"^第[一二三四五六七八九十百0-9]+屆\s*", "", t)
    # 3. Strip bracketed phrases: （...）, (...), 「...」, 《...》, 【...】, [...]
    t = re.sub(r"[（\(「《【\[].*?[）\)」》】\]]", "", t)
    # 4. Strip trailing subtitle delimiters: ｜, ・, ·, —, -, :, ：, #
    t = re.sub(r"[｜・·—\-\:：#].*$", "", t)
    t = t.strip()
    return t


def calculate_date_overlap_ratio(
    start1: Optional[date],
    end1: Optional[date],
    start2: Optional[date],
    end2: Optional[date],
) -> float:
    """Calculate the overlap ratio between two date ranges [start1, end1] and [start2, end2].
    Returns overlap_days / min_span_days.
    """
    if not start1 or not end1 or not start2 or not end2:
        return 0.0

    # Ensure start <= end
    s1, e1 = min(start1, end1), max(start1, end1)
    s2, e2 = min(start2, end2), max(start2, end2)

    latest_start = max(s1, s2)
    earliest_end = min(e1, e2)

    if latest_start > earliest_end:
        return 0.0

    overlap_days = (earliest_end - latest_start).days + 1
    span1_days = (e1 - s1).days + 1
    span2_days = (e2 - s2).days + 1
    min_span = min(span1_days, span2_days)

    if min_span <= 0:
        return 0.0
    return min(1.0, overlap_days / min_span)


def is_entity_match(
    title1: str,
    city1: Optional[str],
    start1: Optional[date],
    end1: Optional[date],
    title2: str,
    city2: Optional[str],
    start2: Optional[date],
    end2: Optional[date],
    min_title_similarity: float = 0.85,
    min_date_overlap: float = 0.50,
) -> Tuple[bool, str]:
    """Determine whether two events represent the same physical real-world event entity.
    Returns (is_match, reason).
    """
    # 1. City must match if both are specified
    c1 = (city1 or "").strip()
    c2 = (city2 or "").strip()
    if c1 and c2 and c1 != c2:
        return False, "city_mismatch"

    norm1 = normalize_title(title1)
    norm2 = normalize_title(title2)

    # Generic short tokens to avoid false positives on words like '講座' or '特展'
    GENERIC_TOKENS = {"", "講座", "特展", "特展室", "展覽", "市集", "活動", "音樂會", "書展"}
    if norm1 in GENERIC_TOKENS or norm2 in GENERIC_TOKENS or len(norm1) < 2 or len(norm2) < 2:
        # Fall back to raw title exact check
        if title1.strip() == title2.strip():
            return True, "exact_raw_title_match"
        return False, "generic_short_token"

    # 2. Check title similarity
    if norm1 == norm2:
        title_matched = True
    elif norm1 in norm2 or norm2 in norm1:
        # Substring match if length is significant
        shorter_len = min(len(norm1), len(norm2))
        title_matched = shorter_len >= 4
    else:
        sim = SequenceMatcher(None, norm1, norm2).ratio()
        title_matched = sim >= min_title_similarity

    if not title_matched:
        return False, "title_similarity_below_threshold"

    # 3. Check date overlap if both have dates
    if start1 and end1 and start2 and end2:
        overlap = calculate_date_overlap_ratio(start1, end1, start2, end2)
        if overlap < min_date_overlap:
            return False, f"date_overlap_insufficient_{overlap:.2f}"
        return True, f"matched_norm_title_and_date_overlap_{overlap:.2f}"

    # If dates are missing or partial, title match alone on specific normalized title suffices
    return True, "matched_norm_title_no_conflicting_dates"


def _to_date(val: Any) -> Optional[date]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val = val.strip()
        if "T" in val:
            return datetime.fromisoformat(val).date()
        try:
            return date.fromisoformat(val)
        except ValueError:
            return None
    return None


def find_canonical_parent(
    existing_records: List[Dict[str, Any]],
    candidate: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Scan existing records to find if a candidate matches any existing event entity.
    Returns the matching record dictionary (to adopt its parent_event_key), or None.
    """
    c_title = candidate.get("title", "")
    c_city = candidate.get("city")
    c_start = _to_date(candidate.get("starts_on") or candidate.get("start_at_tpe"))
    c_end = _to_date(candidate.get("ends_on") or candidate.get("end_at_tpe"))

    for ex in existing_records:
        ex_title = ex.get("title", "")
        ex_city = ex.get("city")
        ex_start = _to_date(ex.get("starts_on") or ex.get("start_at_tpe"))
        ex_end = _to_date(ex.get("ends_on") or ex.get("end_at_tpe"))

        matched, _ = is_entity_match(
            c_title, c_city, c_start, c_end,
            ex_title, ex_city, ex_start, ex_end,
        )
        if matched:
            return ex
    return None
