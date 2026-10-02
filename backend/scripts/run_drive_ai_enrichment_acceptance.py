#!/usr/bin/env python3
"""Synthetic runtime acceptance for provider-agnostic Drive AI enrichment.

Runs from the exact release backend image against the dev-test PostgreSQL
instance. It uses a fixed synthetic identity, synthetic database rows, and an
in-process deterministic fake AI provider. It never calls Google Drive or an
external AI provider. Every row created by this script is tracked by exact ID
or run-scoped unique name and removed in a finally path.
"""

from __future__ import annotations

import asyncio
import uuid

import httpx
from sqlalchemy import delete, select

from app.api.auth import current_user
from app.db.session import SessionLocal
from app.main import app
from app.models.drive import (
    DriveDocument,
    DriveDocumentEnrichmentRun,
    DriveEnrichmentSettings,
    DriveNoteLinkSuggestion,
    NoteDriveDocument,
    ProjectDriveDocument,
)
from app.models.migration_support import EntityTag, Tag
from app.models.note import Note
from app.models.project import Project
from app.services import drive_enrichment
from app.services.ai_enrichment_provider import (
    AIEnrichmentProvider,
    AIProviderError,
    DocumentEnrichmentContext,
    RelatedNoteCandidate,
    RelatedNoteSuggestion,
    TagSuggestion,
)


ACCEPTANCE_USER_SUB = "acceptance-drive-ai-runtime"
ACCEPTANCE_USER = {
    "sub": ACCEPTANCE_USER_SUB,
    "email": "drive-ai-acceptance@example.invalid",
    "name": "Drive AI Runtime Acceptance",
}

STAGE_EXIT_CODES = {
    "seed": 41,
    "default_settings": 42,
    "consent_disabled": 43,
    "enable_consent": 44,
    "enrich_success": 45,
    "verify_tags": 46,
    "cache_hit": 47,
    "accept_suggestion": 48,
    "accept_replay": 49,
    "reject_suggestion": 50,
    "partial_failure": 51,
    "disable_consent": 52,
    "consent_disabled_after_success": 53,
    "cleanup": 54,
}


class AcceptanceStageError(RuntimeError):
    def __init__(self, stage: str, cause: BaseException) -> None:
        super().__init__(f"{stage}: {type(cause).__name__}: {cause}")
        self.stage = stage
        self.cause = cause


class AcceptanceProvider(AIEnrichmentProvider):
    provider_name = "acceptance-fake"
    model_name = "deterministic-v1"

    def __init__(
        self,
        existing_tag_name: str,
        generated_tag_name: str,
        target_note_ids: tuple[str, str],
    ) -> None:
        self.existing_tag_name = existing_tag_name
        self.generated_tag_name = generated_tag_name
        self.target_note_ids = target_note_ids
        self.tag_calls = 0
        self.note_calls = 0
        self.fail_notes = False

    async def suggest_tags(
        self,
        document_context: DocumentEnrichmentContext,
    ) -> list[TagSuggestion]:
        del document_context
        self.tag_calls += 1
        return [
            TagSuggestion(name=self.existing_tag_name, confidence=0.97),
            TagSuggestion(name=self.generated_tag_name, confidence=0.93),
        ]

    async def rank_related_notes(
        self,
        document_context: DocumentEnrichmentContext,
        candidate_notes: list[RelatedNoteCandidate],
    ) -> list[RelatedNoteSuggestion]:
        del document_context
        self.note_calls += 1
        if self.fail_notes:
            raise AIProviderError("acceptance_note_stage_failed")
        candidate_ids = {item.note_id for item in candidate_notes}
        missing = set(self.target_note_ids) - candidate_ids
        if missing:
            raise AIProviderError("acceptance_candidate_missing")
        return [
            RelatedNoteSuggestion(
                note_id=note_id,
                confidence=0.90 - (index * 0.05),
                reason="Synthetic same-project acceptance candidate",
            )
            for index, note_id in enumerate(sorted(self.target_note_ids))
        ]


async def _acceptance_user() -> dict:
    return dict(ACCEPTANCE_USER)


def _expect(response: httpx.Response, expected: int, label: str) -> None:
    if response.status_code != expected:
        raise AssertionError(
            f"{label}: expected HTTP {expected}, got {response.status_code}: "
            f"{response.text[:500]}"
        )


def _json_object(response: httpx.Response, label: str) -> dict:
    try:
        payload = response.json()
    except ValueError as exc:
        raise AssertionError(f"{label}: response was not JSON") from exc
    if not isinstance(payload, dict):
        raise AssertionError(f"{label}: expected JSON object")
    return payload


def _record(check: str) -> None:
    print(f"drive_ai_runtime_check={check}:PASS", flush=True)


async def _seed(
    *,
    project_id: str,
    document_id: str,
    document_name: str,
    note_ids: tuple[str, str],
    existing_tag_id: str,
    existing_tag_name: str,
    google_file_id: str,
    label: str,
) -> None:
    async with SessionLocal() as db:
        db.add(
            Project(
                id=project_id,
                name=f"{label} Project",
                summary=label,
                status="active",
            )
        )
        db.add(
            DriveDocument(
                id=document_id,
                user_sub=ACCEPTANCE_USER_SUB,
                google_file_id=google_file_id,
                name=document_name,
                mime_type="application/vnd.google-apps.document",
                web_view_link=None,
                modified_at=None,
            )
        )
        db.add(Tag(id=existing_tag_id, name=existing_tag_name))
        db.add_all(
            [
                Note(
                    id=note_ids[0],
                    title=f"{label} Related note A",
                    body="Synthetic quarterly research planning candidate A",
                    project_id=project_id,
                ),
                Note(
                    id=note_ids[1],
                    title=f"{label} Related note B",
                    body="Synthetic quarterly research planning candidate B",
                    project_id=project_id,
                ),
            ]
        )
        await db.flush()
        db.add(
            ProjectDriveDocument(
                project_id=project_id,
                drive_document_id=document_id,
            )
        )
        db.add(
            EntityTag(
                entity_type="drive_document",
                entity_id=document_id,
                tag_id=existing_tag_id,
            )
        )
        await db.commit()


async def _verify_tags(
    document_id: str,
    existing_tag_name: str,
    generated_tag_name: str,
) -> None:
    async with SessionLocal() as db:
        names = list(
            (
                await db.execute(
                    select(Tag.name)
                    .join(EntityTag, EntityTag.tag_id == Tag.id)
                    .where(
                        EntityTag.entity_type == "drive_document",
                        EntityTag.entity_id == document_id,
                    )
                )
            ).scalars().all()
        )
        if existing_tag_name not in names:
            raise AssertionError("AI enrichment removed the pre-existing Drive Tag")
        if generated_tag_name not in names:
            raise AssertionError("AI enrichment did not attach its generated Drive Tag")
        if names.count(existing_tag_name) != 1:
            raise AssertionError("Existing Tag vocabulary was duplicated instead of reused")


async def _verify_note_link(
    note_id: str,
    document_id: str,
    *,
    expected: bool,
) -> None:
    async with SessionLocal() as db:
        relation = await db.get(
            NoteDriveDocument,
            {"note_id": note_id, "drive_document_id": document_id},
        )
        if expected:
            if relation is None:
                raise AssertionError("Accepted suggestion did not create Note↔Drive relation")
            if relation.relation_type != "related" or relation.link_source != "ai_accepted":
                raise AssertionError("Accepted suggestion created the wrong authoritative relation")
        elif relation is not None:
            raise AssertionError("Rejected suggestion unexpectedly created Note↔Drive relation")


async def _cleanup(
    *,
    project_id: str,
    document_id: str,
    note_ids: tuple[str, str],
    tag_names: tuple[str, str],
) -> None:
    """Delete only run-scoped synthetic acceptance rows in FK-safe order."""

    async with SessionLocal() as db:
        tag_ids = list(
            (
                await db.execute(
                    select(Tag.id).where(Tag.name.in_(tag_names))
                )
            ).scalars().all()
        )
        await db.execute(
            delete(NoteDriveDocument).where(
                NoteDriveDocument.drive_document_id == document_id
            )
        )
        await db.execute(
            delete(DriveNoteLinkSuggestion).where(
                DriveNoteLinkSuggestion.drive_document_id == document_id
            )
        )
        await db.execute(
            delete(DriveDocumentEnrichmentRun).where(
                DriveDocumentEnrichmentRun.drive_document_id == document_id
            )
        )
        await db.execute(
            delete(DriveEnrichmentSettings).where(
                DriveEnrichmentSettings.user_sub == ACCEPTANCE_USER_SUB
            )
        )
        await db.execute(
            delete(EntityTag).where(
                EntityTag.entity_type == "drive_document",
                EntityTag.entity_id == document_id,
            )
        )
        await db.execute(
            delete(ProjectDriveDocument).where(
                ProjectDriveDocument.drive_document_id == document_id
            )
        )
        await db.execute(delete(Note).where(Note.id.in_(note_ids)))
        await db.execute(delete(Project).where(Project.id == project_id))
        await db.execute(
            delete(DriveDocument).where(
                DriveDocument.id == document_id,
                DriveDocument.user_sub == ACCEPTANCE_USER_SUB,
            )
        )
        if tag_ids:
            await db.execute(
                delete(Tag).where(
                    Tag.id.in_(tag_ids),
                    Tag.name.in_(tag_names),
                )
            )
        await db.commit()

    async with SessionLocal() as db:
        if await db.get(DriveDocument, document_id) is not None:
            raise AssertionError("cleanup left acceptance DriveDocument behind")
        if await db.get(Project, project_id) is not None:
            raise AssertionError("cleanup left acceptance Project behind")
        for note_id in note_ids:
            if await db.get(Note, note_id) is not None:
                raise AssertionError("cleanup left acceptance Note behind")
        if await db.get(DriveEnrichmentSettings, ACCEPTANCE_USER_SUB) is not None:
            raise AssertionError("cleanup left acceptance enrichment settings behind")
        remaining_tags = list(
            (
                await db.execute(select(Tag.name).where(Tag.name.in_(tag_names)))
            ).scalars().all()
        )
        if remaining_tags:
            raise AssertionError("cleanup left acceptance Tags behind")


async def run_acceptance() -> None:
    run_id = str(uuid.uuid4())
    label = f"[ACCEPTANCE TEST] drive-ai {run_id}"
    project_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())
    document_name = f"zz{run_id.replace('-', '')}"
    note_ids = (str(uuid.uuid4()), str(uuid.uuid4()))
    existing_tag_id = str(uuid.uuid4())
    existing_tag_name = f"acceptance-existing-{run_id}"
    generated_tag_name = f"acceptance-ai-{run_id}"
    google_file_id = f"acceptance-drive-ai-file-{run_id}"
    provider = AcceptanceProvider(existing_tag_name, generated_tag_name, note_ids)
    original_provider_resolver = drive_enrichment.get_ai_enrichment_provider
    primary_error: BaseException | None = None
    stage = "seed"

    try:
        await _seed(
            project_id=project_id,
            document_id=document_id,
            document_name=document_name,
            note_ids=note_ids,
            existing_tag_id=existing_tag_id,
            existing_tag_name=existing_tag_name,
            google_file_id=google_file_id,
            label=label,
        )
        drive_enrichment.get_ai_enrichment_provider = lambda: provider
        app.dependency_overrides[current_user] = _acceptance_user
        transport = httpx.ASGITransport(app=app)

        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://acceptance.local",
            timeout=30.0,
        ) as client:
            stage = "default_settings"
            response = await client.get("/api/v1/drive/enrichment/settings")
            _expect(response, 200, "Default enrichment settings")
            settings = _json_object(response, "Default enrichment settings")
            if settings.get("allow_document_content") is not False:
                raise AssertionError("AI content consent did not default OFF")
            _record("consent_defaults_off")

            stage = "consent_disabled"
            response = await client.post(
                f"/api/v1/drive/documents/{document_id}/enrichment",
                json={"force": False},
            )
            _expect(response, 200, "Consent-disabled enrichment")
            skipped = _json_object(response, "Consent-disabled enrichment")
            if skipped.get("status") != "skipped" or skipped.get("error_code") != "consent_disabled":
                raise AssertionError("Consent-disabled enrichment did not return auditable skipped outcome")
            if provider.tag_calls != 0 or provider.note_calls != 0:
                raise AssertionError("Provider was called while AI content consent was OFF")
            _record("consent_disabled_zero_provider_calls")

            stage = "enable_consent"
            response = await client.put(
                "/api/v1/drive/enrichment/settings",
                json={
                    "allow_document_content": True,
                    "auto_tags_enabled": True,
                    "note_suggestions_enabled": True,
                    "max_related_note_suggestions": 5,
                },
            )
            _expect(response, 200, "Enable enrichment consent")
            if _json_object(response, "Enable enrichment consent").get("allow_document_content") is not True:
                raise AssertionError("AI content consent was not persisted ON")
            _record("consent_enabled")

            stage = "enrich_success"
            response = await client.post(
                f"/api/v1/drive/documents/{document_id}/enrichment",
                json={"force": False},
            )
            _expect(response, 200, "Successful enrichment")
            enriched = _json_object(response, "Successful enrichment")
            if enriched.get("status") != "succeeded" or enriched.get("cache_hit") is not False:
                raise AssertionError("First consented enrichment was not a fresh success")
            if provider.tag_calls != 1 or provider.note_calls != 1:
                raise AssertionError("Provider stages were not called exactly once")
            suggestions = enriched.get("note_suggestions") or []
            if len(suggestions) != 2 or any(item.get("decision") != "pending" for item in suggestions):
                raise AssertionError("Expected two pending Note suggestions")
            suggestion_by_note = {str(item["note_id"]): item for item in suggestions}
            if set(suggestion_by_note) != set(note_ids):
                raise AssertionError("Provider suggestions escaped bounded candidate Notes")
            _record("provider_success_persisted")

            stage = "verify_tags"
            await _verify_tags(document_id, existing_tag_name, generated_tag_name)
            _record("tags_additive_and_vocabulary_reused")

            stage = "cache_hit"
            response = await client.post(
                f"/api/v1/drive/documents/{document_id}/enrichment",
                json={"force": False},
            )
            _expect(response, 200, "Cached enrichment")
            cached = _json_object(response, "Cached enrichment")
            if cached.get("status") != "succeeded" or cached.get("cache_hit") is not True:
                raise AssertionError("Stable fingerprint did not reuse successful enrichment cache")
            if cached.get("id") != enriched.get("id"):
                raise AssertionError("Cache hit did not reuse the successful enrichment run")
            if provider.tag_calls != 1 or provider.note_calls != 1:
                raise AssertionError("Cache hit called the provider again")
            _record("stable_fingerprint_cache_hit")

            accepted_note_id = sorted(note_ids)[0]
            rejected_note_id = sorted(note_ids)[1]
            accepted_suggestion_id = str(suggestion_by_note[accepted_note_id]["id"])
            rejected_suggestion_id = str(suggestion_by_note[rejected_note_id]["id"])

            stage = "accept_suggestion"
            response = await client.post(
                f"/api/v1/drive/note-suggestions/{accepted_suggestion_id}/decision",
                json={"decision": "accepted"},
            )
            _expect(response, 200, "Accept Note suggestion")
            if _json_object(response, "Accept Note suggestion").get("decision") != "accepted":
                raise AssertionError("Note suggestion was not accepted")
            await _verify_note_link(accepted_note_id, document_id, expected=True)
            _record("accepted_creates_ai_accepted_relation")

            stage = "accept_replay"
            response = await client.post(
                f"/api/v1/drive/note-suggestions/{accepted_suggestion_id}/decision",
                json={"decision": "accepted"},
            )
            _expect(response, 200, "Accept Note suggestion replay")
            await _verify_note_link(accepted_note_id, document_id, expected=True)
            _record("acceptance_decision_idempotent")

            stage = "reject_suggestion"
            response = await client.post(
                f"/api/v1/drive/note-suggestions/{rejected_suggestion_id}/decision",
                json={"decision": "rejected"},
            )
            _expect(response, 200, "Reject Note suggestion")
            if _json_object(response, "Reject Note suggestion").get("decision") != "rejected":
                raise AssertionError("Note suggestion was not rejected")
            await _verify_note_link(rejected_note_id, document_id, expected=False)
            _record("rejected_does_not_create_relation")

            stage = "partial_failure"
            provider.fail_notes = True
            response = await client.post(
                f"/api/v1/drive/documents/{document_id}/enrichment",
                json={"force": True},
            )
            _expect(response, 200, "Partial provider failure")
            partial = _json_object(response, "Partial provider failure")
            if partial.get("status") != "partial" or partial.get("error_code") != "acceptance_note_stage_failed":
                raise AssertionError("One-stage provider failure was not persisted as partial")
            if generated_tag_name not in (partial.get("suggested_tags") or []):
                raise AssertionError("Partial result discarded the successful Tag stage")
            _record("partial_failure_preserves_successful_stage")

            stage = "disable_consent"
            provider.fail_notes = False
            response = await client.put(
                "/api/v1/drive/enrichment/settings",
                json={"allow_document_content": False},
            )
            _expect(response, 200, "Disable enrichment consent")
            calls_before_opt_out = (provider.tag_calls, provider.note_calls)
            _record("consent_disabled_after_prior_success")

            stage = "consent_disabled_after_success"
            response = await client.post(
                f"/api/v1/drive/documents/{document_id}/enrichment",
                json={"force": False},
            )
            _expect(response, 200, "Post-success consent-disabled enrichment")
            opted_out = _json_object(response, "Post-success consent-disabled enrichment")
            if opted_out.get("status") != "skipped" or opted_out.get("error_code") != "consent_disabled":
                raise AssertionError("Opt-out reused prior AI success instead of returning skipped")
            if (provider.tag_calls, provider.note_calls) != calls_before_opt_out:
                raise AssertionError("Provider was called after AI content consent opt-out")
            _record("opt_out_blocks_provider_and_cached_success")

    except BaseException as exc:
        primary_error = AcceptanceStageError(stage, exc)
    finally:
        drive_enrichment.get_ai_enrichment_provider = original_provider_resolver
        app.dependency_overrides.pop(current_user, None)
        try:
            await _cleanup(
                project_id=project_id,
                document_id=document_id,
                note_ids=note_ids,
                tag_names=(existing_tag_name, generated_tag_name),
            )
            _record("cleanup")
        except BaseException as cleanup_error:
            if primary_error is None:
                raise AcceptanceStageError("cleanup", cleanup_error) from cleanup_error
            print(
                f"drive_ai_runtime_cleanup_error={type(cleanup_error).__name__}:"
                f"{cleanup_error}",
                flush=True,
            )

    if primary_error is not None:
        raise primary_error

    print("drive_ai_runtime_acceptance=PASS", flush=True)


def main() -> int:
    try:
        asyncio.run(run_acceptance())
    except AcceptanceStageError as exc:
        print(
            f"drive_ai_runtime_acceptance=FAIL stage={exc.stage} "
            f"error={type(exc.cause).__name__}:{exc.cause}",
            flush=True,
        )
        return STAGE_EXIT_CODES[exc.stage]
    except BaseException as exc:
        print(
            f"drive_ai_runtime_acceptance=FAIL stage=unknown "
            f"error={type(exc).__name__}:{exc}",
            flush=True,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
