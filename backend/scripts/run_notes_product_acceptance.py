#!/usr/bin/env python3
"""Verify Notes search/tags/links/delete policy against the deployed database."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import uuid

import httpx
from sqlalchemy import delete, or_, select

from app.api.auth import SESSION_COOKIE, current_user
from app.db.session import SessionLocal
from app.main import app, CORE_FEATURE_GATES
from app.models.migration_support import EntityTag, Tag
from app.models.note import Note, NoteLink


ACCEPTANCE_USER = {
    "sub": "acceptance-notes-product",
    "email": "notes-product-acceptance@example.invalid",
    "name": "Notes Product Acceptance",
}


@dataclass
class AcceptanceArtifacts:
    note_ids: set[str] = field(default_factory=set)
    tag_names: set[str] = field(default_factory=set)


async def _acceptance_user() -> dict:
    return dict(ACCEPTANCE_USER)


def _expect(response: httpx.Response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(
            f"{label}: expected HTTP {expected}, got {response.status_code}: "
            f"{response.text[:500]}"
        )


async def _cleanup(artifacts: AcceptanceArtifacts) -> None:
    async with SessionLocal() as db:
        if artifacts.note_ids:
            note_ids = tuple(artifacts.note_ids)
            await db.execute(
                delete(NoteLink).where(
                    or_(
                        NoteLink.source_note_id.in_(note_ids),
                        NoteLink.target_note_id.in_(note_ids),
                    )
                )
            )
            await db.execute(
                delete(EntityTag).where(
                    EntityTag.entity_type == "note",
                    EntityTag.entity_id.in_(note_ids),
                )
            )
            await db.execute(delete(Note).where(Note.id.in_(note_ids)))
        if artifacts.tag_names:
            await db.execute(delete(Tag).where(Tag.name.in_(tuple(artifacts.tag_names))))
        await db.commit()

        if artifacts.note_ids:
            remaining = await db.execute(
                select(Note.id).where(Note.id.in_(tuple(artifacts.note_ids)))
            )
            if remaining.first() is not None:
                raise AssertionError("notes acceptance cleanup left note rows")
        if artifacts.tag_names:
            remaining_tags = await db.execute(
                select(Tag.id).where(Tag.name.in_(tuple(artifacts.tag_names)))
            )
            if remaining_tags.first() is not None:
                raise AssertionError("notes acceptance cleanup left tag rows")


def _ids(response: httpx.Response) -> set[str]:
    payload = response.json()
    if not isinstance(payload, list):
        raise AssertionError("expected JSON list")
    return {str(item["id"]) for item in payload}


async def run_acceptance() -> None:
    artifacts = AcceptanceArtifacts()
    run_id = uuid.uuid4().hex[:12]
    needle = f"needle-{run_id}"
    chinese_fragment = f"旅行{run_id[:4]}"
    tag_a = f"[ACCEPTANCE TEST] note-tag-{run_id}"
    tag_b = f"[ACCEPTANCE TEST] important-{run_id}"
    artifacts.tag_names.update({tag_a, tag_b})

    app.dependency_overrides[current_user] = _acceptance_user
    # Test Notes behavior independently of admin rollout in this isolated runner.
    app.dependency_overrides[CORE_FEATURE_GATES["notes"]] = lambda: None
    transport = httpx.ASGITransport(app=app)

    try:
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://acceptance.local",
            timeout=30.0,
            cookies={SESSION_COOKIE: "id:acceptance"},
        ) as client:
            response = await client.post(
                "/api/v1/notes",
                json={
                    "title": f"[ACCEPTANCE TEST] {chinese_fragment} 筆記",
                    "body": f"PostgreSQL full text {needle} markdown **preview**",
                    "project_id": None,
                },
            )
            _expect(response, 201, "note A create")
            note_a = str(response.json()["id"])
            artifacts.note_ids.add(note_a)

            response = await client.post(
                "/api/v1/notes",
                json={
                    "title": f"[ACCEPTANCE TEST] unrelated-{run_id}",
                    "body": "control note",
                    "project_id": None,
                },
            )
            _expect(response, 201, "note B create")
            note_b = str(response.json()["id"])
            artifacts.note_ids.add(note_b)

            response = await client.get("/api/v1/notes", params={"q": needle})
            _expect(response, 200, "ASCII FTS search")
            if _ids(response) != {note_a}:
                raise AssertionError("ASCII FTS search did not isolate the target note")
            print("notes_acceptance_check=postgres_fts:PASS", flush=True)

            response = await client.get(
                "/api/v1/notes",
                params={"q": chinese_fragment[0:4]},
            )
            _expect(response, 200, "Chinese substring search")
            if note_a not in _ids(response):
                raise AssertionError("Chinese substring fallback did not find target note")
            print("notes_acceptance_check=cjk_substring_fallback:PASS", flush=True)

            response = await client.put(
                f"/api/v1/notes/{note_a}/tags",
                json={"tags": [tag_a, tag_b, tag_a]},
            )
            _expect(response, 200, "replace note tags")
            if set(response.json().get("tags") or []) != {tag_a, tag_b}:
                raise AssertionError("tag replacement did not normalize duplicates")

            response = await client.get(f"/api/v1/notes/{note_a}/tags")
            _expect(response, 200, "list note tags")
            if set(response.json().get("tags") or []) != {tag_a, tag_b}:
                raise AssertionError("tag persistence reread mismatch")
            print("notes_acceptance_check=tags:PASS", flush=True)

            response = await client.post(
                f"/api/v1/notes/{note_a}/links",
                json={"target_note_id": note_b},
            )
            _expect(response, 204, "create note link")

            response = await client.get(f"/api/v1/notes/{note_a}/links")
            _expect(response, 200, "list note links")
            if note_b not in _ids(response):
                raise AssertionError("linked note was not visible")

            response = await client.delete(
                f"/api/v1/notes/{note_a}/links/{note_b}"
            )
            _expect(response, 204, "delete note link")

            response = await client.get(f"/api/v1/notes/{note_a}/links")
            _expect(response, 200, "reread note links")
            if note_b in _ids(response):
                raise AssertionError("unlinked note was still visible")
            print("notes_acceptance_check=bidirectional_links:PASS", flush=True)

            response = await client.delete(f"/api/v1/notes/{note_a}")
            _expect(response, 409, "delete without explicit confirmation")
            if (response.json().get("error") or {}).get("code") != "confirmation_required":
                raise AssertionError("note delete did not return confirmation_required")

            response = await client.delete(
                f"/api/v1/notes/{note_a}",
                headers={
                    "X-Life-Assistant-Confirmation":
                        f"explicit_user:note.delete:{note_a}",
                },
            )
            _expect(response, 204, "delete note A with explicit confirmation")
            artifacts.note_ids.discard(note_a)

            response = await client.delete(
                f"/api/v1/notes/{note_b}",
                headers={
                    "X-Life-Assistant-Confirmation":
                        f"explicit_user:note.delete:{note_b}",
                },
            )
            _expect(response, 204, "delete note B with explicit confirmation")
            artifacts.note_ids.discard(note_b)
            print("notes_acceptance_check=delete_confirmation:PASS", flush=True)
    finally:
        app.dependency_overrides.pop(current_user, None)
        app.dependency_overrides.pop(CORE_FEATURE_GATES["notes"], None)
        await _cleanup(artifacts)

    print("notes_product_acceptance=PASS", flush=True)


def main() -> None:
    asyncio.run(run_acceptance())


if __name__ == "__main__":
    main()
