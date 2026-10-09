"""Offline deterministic event admission; NEVER fetch a URL or mutate a provider."""
from __future__ import annotations

import hashlib
import ipaddress
import json
from datetime import date, datetime
from decimal import Decimal
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def safe_provenance_url(value: str) -> str:
    """Canonicalize public HTTPS URLs; URL validation is NOT an SSRF-safe fetcher."""
    parts = urlsplit(value.strip())
    hostname = (parts.hostname or "").lower().rstrip(".")
    if (parts.scheme != "https" or not hostname or parts.username or parts.password or parts.port not in (None, 443)):
        raise ValueError("only public HTTPS provenance URLs are accepted")
    if hostname == "localhost" or hostname.endswith(".localhost") or hostname.endswith(".local") or "." not in hostname:
        raise ValueError("non-public hostname")
    try:
        ip = ipaddress.ip_address(hostname.strip("[]"))
    except ValueError:
        # A domain is not resolvable or fetched by this module.
        if any(c.isspace() for c in hostname) or hostname.endswith(".internal"):
            raise ValueError("invalid public hostname")
    else:
        if not ip.is_global:
            raise ValueError("non-public IP")
    if parts.fragment:
        raise ValueError("fragments are not canonical evidence references")
    return urlunsplit(("https", hostname, parts.path or "/", parts.query, ""))


def _aware(value: datetime | None) -> datetime | None:
    if value is not None and (value.tzinfo is None or value.utcoffset() is None):
        raise ValueError("timestamp requires an explicit UTC offset")
    return value


class CandidateOpportunity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    opportunity_key: str = Field(min_length=1, max_length=128)
    registration_url: str | None = None
    opens_at: datetime | None = None
    closes_at: datetime | None = None
    fee_kind: str = "unknown"
    fee_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    fee_currency: str | None = Field(default=None, min_length=3, max_length=3)
    eligibility_note: str | None = Field(default=None, max_length=400)
    registration_status: str = "unannounced"
    official_verified: bool = False

    @field_validator("registration_url")
    @classmethod
    def registration_https(cls, value):
        return safe_provenance_url(value) if value is not None else None

    @field_validator("opens_at", "closes_at")
    @classmethod
    def check_timezone(cls, value):
        return _aware(value)

    @field_validator("fee_kind")
    @classmethod
    def fee_vocab(cls, value):
        if value not in {"free", "conditional_free", "paid", "unknown"}:
            raise ValueError("unknown fee classification")
        return value

    @field_validator("registration_status")
    @classmethod
    def status_vocab(cls, value):
        if value not in {"unannounced", "upcoming", "open", "full",
                         "waitlist_available", "closed", "cancelled", "event_ended"}:
            raise ValueError("unknown registration status")
        return value

    @model_validator(mode="after")
    def validate_window_and_fee(self):
        if self.opens_at is not None and self.closes_at is not None and self.closes_at <= self.opens_at:
            raise ValueError("invalid registration time range")
        if self.fee_kind == "free" and self.fee_amount not in (None, Decimal("0")):
            raise ValueError("verified-free cannot have a positive fee")
        if self.fee_amount is not None and self.fee_currency is None:
            raise ValueError("fee currency missing")
        if self.official_verified and self.fee_kind in {"free", "conditional_free"} and not self.registration_url:
            raise ValueError("free claim needs official registration evidence")
        return self


class CandidateSession(BaseModel):
    model_config = ConfigDict(extra="forbid")
    session_key: str = Field(min_length=1, max_length=128)
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    starts_on: date | None = None
    ends_on_exclusive: date | None = None
    timezone_name: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=100)
    venue: str | None = Field(default=None, max_length=300)
    is_cancelled: bool = False
    opportunities: list[CandidateOpportunity] = Field(default_factory=list)

    @field_validator("starts_at", "ends_at")
    @classmethod
    def check_timezone(cls, value):
        return _aware(value)

    @model_validator(mode="after")
    def validate_session(self):
        if (self.starts_at is not None or self.ends_at is not None) and (
            self.starts_on is not None or self.ends_on_exclusive is not None
        ):
            raise ValueError("all-day dates cannot be mixed with timestamps")
        if self.ends_at is not None and self.starts_at is not None and self.ends_at <= self.starts_at:
            raise ValueError("session end must be after start")
        if self.ends_on_exclusive is not None and self.starts_on is not None and self.ends_on_exclusive <= self.starts_on:
            raise ValueError("all-day exclusive end must be after start")
        if len({o.opportunity_key for o in self.opportunities}) != len(self.opportunities):
            raise ValueError("duplicate registration opportunity key within session")
        return self


class EventCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_id: str = Field(pattern=r"^[a-z0-9_]{2,80}$")
    external_event_key: str = Field(min_length=1, max_length=255)
    title: str = Field(min_length=1, max_length=500)
    summary: str | None = Field(default=None, max_length=600)
    category: str | None = Field(default=None, max_length=80)
    source_url: str
    official_url: str | None = None
    organizer_name: str | None = Field(default=None, max_length=500)
    organizer_url: str | None = None
    official_verified: bool = False
    sessions: list[CandidateSession] = Field(default_factory=list)

    @field_validator("source_url", "official_url", "organizer_url")
    @classmethod
    def url_provenance(cls, value):
        return safe_provenance_url(value) if value is not None else None

    @model_validator(mode="after")
    def validate_identity(self):
        if self.official_verified and not self.official_url:
            raise ValueError("official verification requires official URL")
        if len({session.session_key for session in self.sessions}) != len(self.sessions):
            raise ValueError("duplicate session key within event")
        return self


def canonical_event_key(candidate: EventCandidate) -> str:
    """Never merge two aggregators on title/date; only verified official URL may cross source."""
    if candidate.official_verified:
        basis = "official:" + candidate.official_url
    else:
        basis = "source:" + candidate.source_id + ":" + candidate.external_event_key
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def meaningful_fingerprint(candidate: EventCandidate) -> str:
    """Ignore order, scan time and visual-only site changes. Never infer missing fields."""
    data = candidate.model_dump(mode="json", exclude_none=False)
    # Identity is a key, not content. Normalized nested ordering avoids repeated AI work.
    data.pop("external_event_key")
    data["sessions"].sort(key=lambda value: value["session_key"])
    for session in data["sessions"]:
        session["opportunities"].sort(key=lambda value: value["opportunity_key"])
    payload = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def should_enqueue_ai(old_fingerprint: str | None, new_fingerprint: str,
                      deterministic_is_sufficient: bool) -> bool:
    """AI is never an unconditional per-scan cost."""
    return bool(old_fingerprint != new_fingerprint and not deterministic_is_sufficient)
