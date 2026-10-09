"""Public free-event discovery read DTOs (no personal actions or speculative fees)."""
from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict


class FreeEventOpportunityCard(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    session_id: str
    opportunity_id: str
    title: str
    summary: str | None
    category: str | None
    city: str | None
    venue: str | None
    starts_at: datetime | None
    ends_at: datetime | None
    starts_on: date | None
    ends_on_exclusive: date | None
    timezone_name: str | None
    fee_kind: Literal["free", "conditional_free"]
    fee_amount: Decimal | None
    fee_currency: str | None
    eligibility_note: str | None
    official_url: str
    registration_url: str
    registration_opens_at: datetime | None
    registration_closes_at: datetime | None
    registration_status: str
    window_confirmed_open: bool
    verified_at: datetime
    notice: Literal["external_registration_requires_recheck"] = (
        "external_registration_requires_recheck"
    )


class FreeEventDiscoveryOut(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[FreeEventOpportunityCard]
    returned: int
    last_updated_at: datetime
    policy: Literal["verified_public_catalog_only"] = "verified_public_catalog_only"
