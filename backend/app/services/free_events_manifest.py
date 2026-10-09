"""Bounded, no-network M1 manifest preview; never confers registration validity."""
from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import ValidationError

from app.services.free_events_normalization import (
    EventCandidate, canonical_event_key, meaningful_fingerprint,
)


def prepare_manifest(
    candidate_rows: Iterable[Mapping[str, Any]],
    registry: Mapping[str, Any],
    *,
    previous_fingerprints: Mapping[str, str] | None = None,
    max_rows: int = 5000,
) -> dict[str, Any]:
    """Preview dedup/quality without SQL, HTTP, model calls or side effects.

    Values from JSONL are untrusted even if they claim official_verified=True.
    Neither 'eligible_for_review' nor any other result is a publication decision.
    """
    known = {item["id"]: item for item in registry["sources"]}
    previous_fingerprints = previous_fingerprints or {}
    index: dict[str, dict[str, Any]] = {}
    rejected = Counter()
    duplicates = 0
    count = 0

    for raw in candidate_rows:
        count += 1
        if count > max_rows:
            raise ValueError("candidate batch exceeds bounded maximum")
        try:
            candidate = EventCandidate.model_validate(raw)
        except (ValidationError, ValueError):
            rejected["invalid_candidate"] += 1
            continue
        source = known.get(candidate.source_id)
        if source is None:
            rejected["unknown_source"] += 1
            continue
        key = canonical_event_key(candidate)
        fingerprint = meaningful_fingerprint(candidate)
        approved = (
            source.get("service_access_review") == "reviewed_with_evidence"
            and source.get("enabled_for_fetch") is True
            and bool(source.get("data_license_evidence"))
        )
        record = index.get(key)
        if record is None:
            record = {
                "event_key": key,
                "fingerprint": fingerprint,
                "provenance_sources": set(),
                "source_approved": approved,
                "official_claimed": candidate.official_verified,
                "session_count": len(candidate.sessions),
                "registration_count": sum(len(s.opportunities) for s in candidate.sessions),
                "unknown_fee_count": sum(
                    1 for s in candidate.sessions for o in s.opportunities
                    if o.fee_kind == "unknown"
                ),
                "unknown_registration_start_count": sum(
                    1 for s in candidate.sessions for o in s.opportunities
                    if o.opens_at is None
                ),
                "content_conflict": False,
            }
            index[key] = record
        else:
            if record["fingerprint"] == fingerprint:
                duplicates += 1
            else:
                record["content_conflict"] = True
            # A duplicated unapproved record must never override an approved
            # provenance, but disagreement always blocks manual publication.
            record["source_approved"] = record["source_approved"] or approved
            record["official_claimed"] = record["official_claimed"] and candidate.official_verified
        record["provenance_sources"].add(candidate.source_id)

    summary = Counter()
    output = []
    for key, record in sorted(index.items()):
        if record["content_conflict"]:
            status = "conflict_requires_review"
        elif not record["source_approved"]:
            status = "quarantined_source_permission"
        elif not record["official_claimed"]:
            status = "needs_official_review"
        else:
            status = "eligible_for_manual_review"
        summary[status] += 1
        output.append({
            **record,
            "provenance_sources": sorted(record["provenance_sources"]),
            "status": status,
            "unchanged_from_previous": previous_fingerprints.get(key) == record["fingerprint"],
            "publishable": False,
            "registration_open_verified": False,
        })
    return {
        "m1_status": "PARTIAL",
        "provider_sync_status": "NOT_VERIFIED",
        "network_requests": 0,
        "database_writes": 0,
        "ai_calls": 0,
        "input_count": count,
        "deduplicated_count": duplicates,
        "rejected": dict(sorted(rejected.items())),
        "status_counts": dict(sorted(summary.items())),
        "candidates": output,
    }
