#!/usr/bin/env python3
"""Offline-only M0 provenance / freshness report, intentionally no network I/O.

This is NOT a scraper or an acceptance certificate. The 14-day evidence must
be supplied from independent, source-authorized observations and reviewed.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REGISTRY = ROOT / "data/free_events_m0_sources.json"
APPROVED_STATES = {"reviewed_with_evidence"}
SERVICE_STATES = APPROVED_STATES | {
    "pending", "pending_api_credentials_and_rate_limits",
    "pending_robots_terms_or_authorized_api",
}
TIERS = {"official_dataset", "official_api", "official_catalog", "aggregator"}


def _https_url(value: str | None) -> bool:
    if not isinstance(value, str):
        return False
    url = urlparse(value)
    return url.scheme == "https" and bool(url.hostname) and not url.username and not url.password


def load_registry(path: Path = DEFAULT_REGISTRY) -> dict:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema_version") != 1 or not isinstance(document.get("sources"), list):
        raise ValueError("invalid registry version or sources")
    if len(document["sources"]) == 0:
        raise ValueError("empty source registry")
    source_ids = set()
    for source in document["sources"]:
        source_id = source.get("id")
        if not isinstance(source_id, str) or not source_id.isascii() or not source_id.replace("_", "").isalnum():
            raise ValueError("invalid source id")
        if source_id in source_ids:
            raise ValueError("duplicate source id")
        source_ids.add(source_id)
        if source.get("tier") not in TIERS:
            raise ValueError("unknown tier")
        if not _https_url(source.get("reference_url")):
            raise ValueError("missing HTTPS source provenance")
        if source.get("service_access_review") not in SERVICE_STATES:
            raise ValueError("unknown access review state")
        if type(source.get("enabled_for_fetch")) is not bool:
            raise ValueError("enabled_for_fetch must be boolean")
        if source["enabled_for_fetch"]:
            if source["service_access_review"] not in APPROVED_STATES:
                raise ValueError("unreviewed source cannot fetch")
            if not _https_url(source.get("data_license_evidence")):
                raise ValueError("enabled source must have license evidence")
            if source.get("requires_api_key") is True and not source.get("credential_reference"):
                raise ValueError("enabled authenticated source must reference non-secret credential")
        hours = source.get("expected_interval_hours")
        if not isinstance(hours, int) or isinstance(hours, bool) or not 1 <= hours <= 168:
            raise ValueError("invalid observation interval")
        if source["tier"] == "aggregator" and source["enabled_for_fetch"]:
            if not _https_url(source.get("endpoint_documentation_url")):
                raise ValueError("aggregator requires reviewed authorized endpoint")
    return document


def _aware_time(value: str) -> datetime:
    if not isinstance(value, str):
        raise ValueError("time must be ISO8601 string")
    t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if t.tzinfo is None or t.utcoffset() is None:
        raise ValueError("observation time must include timezone")
    return t.astimezone(timezone.utc)


def _max_consecutive_day_run(days: set[str]) -> int:
    dates = sorted(datetime.fromisoformat(day).date() for day in days)
    best = current = 0
    previous = None
    for day in dates:
        current = current + 1 if previous is not None and day == previous + timedelta(days=1) else 1
        best = max(best, current)
        previous = day
    return best


def evaluate(registry: dict, observations: list[dict], *, as_of: datetime) -> dict:
    """Never label M0 PASS based only on local JSONL data."""
    as_of = as_of.astimezone(timezone.utc)
    sources = {item["id"]: item for item in registry["sources"]}
    by_source = defaultdict(lambda: {
        "days": set(), "sample_count": 0, "free_confirmed": 0,
        "free_unverified": 0, "fee_unknown": 0,
        "registration_open_unknown": 0, "official_page_unverified": 0,
        "latency_hours": [],
    })
    for obj in observations:
        source_id = obj.get("source_id")
        if source_id not in sources:
            raise ValueError("unknown source in observations")
        observed = _aware_time(obj.get("observed_at"))
        if observed > as_of:
            raise ValueError("future observation is not allowed")
        if obj.get("is_free") not in (True, False, None):
            raise ValueError("is_free must be true/false/null")
        if type(obj.get("official_verified")) is not bool:
            raise ValueError("official_verified must be explicit boolean")
        if not isinstance(obj.get("event_key"), str) or not obj["event_key"].strip():
            raise ValueError("opaque event key is required")
        record = by_source[source_id]
        record["days"].add(observed.date().isoformat())
        record["sample_count"] += 1
        if obj["is_free"] is None:
            record["fee_unknown"] += 1
        elif obj["is_free"] is True:
            record["free_confirmed" if obj["official_verified"] else "free_unverified"] += 1
        if not obj["official_verified"]:
            record["official_page_unverified"] += 1
        registration = obj.get("registration_opens_at")
        if registration is None:
            record["registration_open_unknown"] += 1
        else:
            _aware_time(registration)
        published = obj.get("published_at")
        if published is not None:
            pub = _aware_time(published)
            if pub > observed:
                raise ValueError("publication time after observed time")
            record["latency_hours"].append(round((observed - pub).total_seconds() / 3600, 3))
    results = {}
    for source_id, source in sources.items():
        record = by_source[source_id]
        consecutive = _max_consecutive_day_run(record["days"])
        latency = record["latency_hours"]
        results[source_id] = {
            "tier": source["tier"],
            "access_review": source["service_access_review"],
            "fetch_enabled": source["enabled_for_fetch"],
            "observation_days": len(record["days"]),
            "max_consecutive_days": consecutive,
            "fourteen_day_window_observed": consecutive >= 14,
            "sample_count": record["sample_count"],
            "free_confirmed": record["free_confirmed"],
            "free_unverified": record["free_unverified"],
            "fee_unknown": record["fee_unknown"],
            "registration_open_unknown": record["registration_open_unknown"],
            "official_page_unverified": record["official_page_unverified"],
            "publication_latency_samples": len(latency),
            "mean_publication_latency_hours": round(sum(latency) / len(latency), 3) if latency else None,
        }
    return {
        "m0_status": "NOT_VERIFIED",
        "reason": "M0 requires 14-day real observations, source permission reviews and human quality acceptance; synthetic fixtures never count.",
        "as_of": as_of.isoformat(),
        "registry_source_count": len(sources),
        "automated_fetch_enabled_count": sum(s["enabled_for_fetch"] for s in sources.values()),
        "sources": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline-only M0 baseline; no network")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--observations", type=Path, default=None)
    parser.add_argument("--as-of", default=None)
    args = parser.parse_args()
    registry = load_registry(args.registry)
    rows = []
    if args.observations is not None:
        with args.observations.open(encoding="utf-8") as file:
            for line in file:
                if line.strip():
                    rows.append(json.loads(line))
    now = _aware_time(args.as_of) if args.as_of is not None else datetime.now(timezone.utc)
    print(json.dumps(evaluate(registry, rows, as_of=now), ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
