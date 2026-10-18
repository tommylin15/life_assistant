"""Public, source-reviewed user changelog for API-only maintenance releases.

There is no independent database, scheduler, user information or admin editor.
Only add a note for a user-observable change when verified release gates exist.
Notes become public on the Cloud Run revision that is actually promoted.
"""
from datetime import date

from fastapi import APIRouter, Response
from pydantic import BaseModel, Field

router = APIRouter(tags=["release-notes"])


class BackendReleaseNote(BaseModel):
    id: str = Field(pattern=r"^backend-[0-9]{8}-[a-z0-9-]+$")
    title: str = Field(min_length=2, max_length=80)
    changes: list[str] = Field(min_length=1, max_length=3)
    published_on: date
    feature_key: str | None = None


# No API-only user-visible fixes have been verified for publication yet.
# A newly promoted backend can publish notes without redeploying Flutter Web.
# Future entries must be written as BackendReleaseNote(...) and validated in CI.
PUBLISHED_NOTES: tuple[BackendReleaseNote, ...] = ()


@router.get("/release-notes")
def release_notes(response: Response) -> dict[str, list[dict]]:
    response.headers["Cache-Control"] = "no-store"
    return {"notes": [note.model_dump(mode="json") for note in PUBLISHED_NOTES]}
